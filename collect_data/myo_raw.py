# https://github.com/dzhu/myo-raw/issues/8

'''
	Original by dzhu
		https://github.com/dzhu/myo-raw

	Edited by Fernando Cosentino
        http://www.fernandocosentino.net/pyoconnect

    Edited by Alvaro Villoslada (Alvipe)
        https://github.com/Alvipe/myo-raw

    Edited by Robert Schloen
        https://github.com/rschloen/semg_control/tree/b76d0fc9b0583eb0f954d9bbf23f4af748efa498

    Edited by Sonia Yuxiao Lai
'''

from __future__ import print_function

import enum
import re
import struct
import sys
import threading
import time
import csv
import serial
from serial.tools.list_ports import comports

from common import *

def multichr(ords):
    if sys.version_info[0] >= 3:
        return bytes(ords)
    else:
        return ''.join(map(chr, ords))

def multiord(b):
    if sys.version_info[0] >= 3:
        return list(b)
    else:
        return map(ord, b)

class Arm(enum.Enum):
    UNKNOWN = 0
    RIGHT = 1
    LEFT = 2

class XDirection(enum.Enum):
    UNKNOWN = 0
    X_TOWARD_WRIST = 1
    X_TOWARD_ELBOW = 2

class Pose(enum.Enum):
    REST = 0
    FIST = 1
    WAVE_IN = 2
    WAVE_OUT = 3
    FINGERS_SPREAD = 4
    THUMB_TO_PINKY = 5
    UNKNOWN = 255


class Packet(object):
    def __init__(self, ords):
        self.typ = ords[0]
        self.cls = ords[2]
        self.cmd = ords[3]
        self.payload = multichr(ords[4:])

    def __repr__(self):
        return 'Packet(%02X, %02X, %02X, [%s])' % \
            (self.typ, self.cls, self.cmd,
             ' '.join('%02X' % b for b in multiord(self.payload)))


class BT(object):
    '''Implements the non-Myo-specific details of the Bluetooth protocol.'''
    def __init__(self, tty):
        self.ser = serial.Serial(port=tty, baudrate=9600, dsrdtr=1)
        self.buf = []
        self.lock = threading.Lock()
        self.handlers = []

    ## internal data-handling methods
    def recv_packet(self, timeout=None):
        t0 = time.time()
        self.ser.timeout = None
        while timeout is None or time.time() < t0 + timeout:
            if timeout is not None: self.ser.timeout = t0 + timeout - time.time()
            c = self.ser.read()
            if not c: return None

            ret = self.proc_byte(ord(c))
            if ret:
                if ret.typ == 0x80:
                    self.handle_event(ret)
                return ret

    def recv_packets(self, timeout=.5):
        res = []
        t0 = time.time()
        while time.time() < t0 + timeout:
            p = self.recv_packet(t0 + timeout - time.time())
            if not p: return res
            res.append(p)
        return res

    def proc_byte(self, c):
        if not self.buf:
            if c in [0x00, 0x80, 0x08, 0x88]:
                self.buf.append(c)
            return None
        elif len(self.buf) == 1:
            self.buf.append(c)
            self.packet_len = 4 + (self.buf[0] & 0x07) + self.buf[1]
            return None
        else:
            self.buf.append(c)

        if self.packet_len and len(self.buf) == self.packet_len:
            p = Packet(self.buf)
            self.buf = []
            return p
        return None

    def handle_event(self, p):
        for h in self.handlers:
            h(p)

    def add_handler(self, h):
        self.handlers.append(h)

    def remove_handler(self, h):
        try: self.handlers.remove(h)
        except ValueError: pass

    def wait_event(self, cls, cmd):
        res = [None]
        def h(p):
            if p.cls == cls and p.cmd == cmd:
                res[0] = p
        self.add_handler(h)
        while res[0] is None:
            self.recv_packet()
        self.remove_handler(h)
        return res[0]

    ## specific BLE commands
    def connect(self, addr):
        return self.send_command(6, 3, pack('6sBHHHH', multichr(addr), 0, 6, 6, 64, 0))

    def get_connections(self):
        return self.send_command(0, 6)

    def discover(self):
        return self.send_command(6, 2, b'\x01')

    def end_scan(self):
        return self.send_command(6, 4)

    def disconnect(self, h):
        return self.send_command(3, 0, pack('B', h))

    def read_attr(self, con, attr):
        self.send_command(4, 4, pack('BH', con, attr))
        return self.wait_event(4, 5)

    def write_attr(self, con, attr, val):
        self.send_command(4, 5, pack('BHB', con, attr, len(val)) + val)
        return self.wait_event(4, 1)

    def send_command(self, cls, cmd, payload=b'', wait_resp=True):
        s = pack('4B', 0, len(payload), cls, cmd) + payload
        self.ser.write(s)

        while True:
            p = self.recv_packet()

            ## no timeout, so p won't be None
            if p.typ == 0: return p

            ## not a response: must be an event
            self.handle_event(p)


class MyoRaw(object):
    '''Implements the Myo-specific communication protocol.'''

    def __init__(self, tty=None):
        if tty is None:
            tty = self.detect_tty()
        if tty is None:
            raise ValueError('Myo dongle not found!')

        self.bt = BT(tty)
        self.conn = None
        self.emg_handlers = []
        self.imu_handlers = []
        self.arm_handlers = []
        self.pose_handlers = []

    def detect_tty(self):
        for p in comports():
            if re.search(r'PID=2458:0*1', p[2]):
                print('using device:', p[0])
                return p[0]

        return None

    def run(self, timeout=None):
        return self.bt.recv_packet(timeout) 

    def connect(self):
        ## stop everything from before
        self.bt.end_scan()
        self.bt.disconnect(0)
        self.bt.disconnect(1)
        self.bt.disconnect(2)

        ## start scanning
        print('scanning...')
        self.bt.discover()
        while True:
            p = self.bt.recv_packet()
            print('scan response:', p)

            if p.payload.endswith(b'\x06\x42\x48\x12\x4A\x7F\x2C\x48\x47\xB9\xDE\x04\xA9\x01\x00\x06\xD5'):
                addr = list(multiord(p.payload[2:8]))
                break
        self.bt.end_scan()

        ## connect and wait for status event
        conn_pkt = self.bt.connect(addr)
        self.conn = multiord(conn_pkt.payload)[-1]
        self.bt.wait_event(3, 0)

        ## get firmware version
        fw = self.read_attr(0x17)
        _, _, _, _, v0, v1, v2, v3 = unpack('BHBBHHHH', fw.payload)
        print('firmware version: %d.%d.%d.%d' % (v0, v1, v2, v3))

        self.old = (v0 == 0)

        if self.old:
            ## don't know what these do; Myo Connect sends them, though we get data
            ## fine without them
            self.write_attr(0x19, b'\x01\x02\x00\x00')
            # Subscribe for notifications from 4 EMG data channels
            self.write_attr(0x2f, b'\x01\x00')
            self.write_attr(0x2c, b'\x01\x00')
            self.write_attr(0x32, b'\x01\x00')
            self.write_attr(0x35, b'\x01\x00')

            ## enable EMG data
            self.write_attr(0x28, b'\x01\x00')
            ## enable IMU data
            self.write_attr(0x1d, b'\x01\x00')

            ## Sampling rate of the underlying EMG sensor, capped to 1000. If it's
            ## less than 1000, emg_hz is correct. If it is greater, the actual
            ## framerate starts dropping inversely. Also, if this is much less than
            ## 1000, EMG data becomes slower to respond to changes. In conclusion,
            ## 1000 is probably a good value.
            C = 1000
            emg_hz = 50
            ## strength of low-pass filtering of EMG data
            emg_smooth = 100

            imu_hz = 50

            ## send sensor parameters, or we don't get any data
            self.write_attr(0x19, pack('BBBBHBBBBB', 2, 9, 2, 1, C, emg_smooth, C // emg_hz, imu_hz, 0, 0))

        else:
            name = self.read_attr(0x03)
            print('device name: %s' % name.payload)

            ## enable IMU data
            self.write_attr(0x1d, b'\x01\x00')
            ## enable on/off arm notifications
            self.write_attr(0x24, b'\x02\x00')

            # self.write_attr(0x19, b'\x01\x03\x00\x01\x01')
            self.start_raw()

        # add data handlers
        def handle_data(p):
            if (p.cls, p.cmd) != (4, 5):
                return

            c, attr, typ = unpack('BHB', p.payload[:4])
            pay = p.payload[5:]

            if attr == 0x27:
                # Unpack a 17 byte array, first 16 are 8 unsigned shorts, last one an unsigned char
                vals = unpack('8HB', pay)
                # not entirely sure what the last byte is, but it's a bitmask that
                # seems to indicate which sensors think they're being moved around or
                # something
                emg = vals[:8]
                moving = vals[8]
                self.on_emg(emg, moving)
            # Read notification handles corresponding to the for EMG characteristics
            elif attr == 0x2b or attr == 0x2e or attr == 0x31 or attr == 0x34:
                '''According to http://developerblog.myo.com/myocraft-emg-in-the-bluetooth-protocol/
                each characteristic sends two secuential readings in each update,
                so the received payload is split in two samples. According to the
                Myo BLE specification, the data type of the EMG samples is int8_t.
                '''
                emg1 = struct.unpack('<8b', pay[:8])
                emg2 = struct.unpack('<8b', pay[8:])
                self.on_emg(emg1, 0)
                self.on_emg(emg2, 0)
            # Read IMU characteristic handle
            elif attr == 0x1c:
                vals = unpack('10h', pay)
                quat = vals[:4]
                acc = vals[4:7]
                gyro = vals[7:10]
                self.on_imu(quat, acc, gyro)
            # Read classifier characteristic handle
            elif attr == 0x23:
                typ, val, xdir, _, _, _ = unpack('6B', pay)

                if typ == 1:  # on arm
                    self.on_arm(Arm(val), XDirection(xdir))
                elif typ == 2:  # removed from arm
                    self.on_arm(Arm.UNKNOWN, XDirection.UNKNOWN)
                elif typ == 3:  # pose
                    self.on_pose(Pose(val))
            # Read battery characteristic handle
            elif attr == 0x11:
                battery_level = ord(pay)
                self.on_battery(battery_level)
            else:
                print('data with unknown attr: %02X %s' % (attr, p))

        self.bt.add_handler(handle_data)


    def write_attr(self, attr, val):
        if self.conn is not None:
            self.bt.write_attr(self.conn, attr, val)

    def read_attr(self, attr):
        if self.conn is not None:
            return self.bt.read_attr(self.conn, attr)
        return None

    def disconnect(self):
        if self.conn is not None:
            self.bt.disconnect(self.conn)

    def start_raw(self):
        ''' To get raw EMG signals, we subscribe to the four EMG notification
        characteristics by writing a 0x0100 command to the corresponding handles.
        '''
        self.write_attr(0x2c, b'\x01\x00')  # Suscribe to EmgData0Characteristic
        self.write_attr(0x2f, b'\x01\x00')  # Suscribe to EmgData1Characteristic
        self.write_attr(0x32, b'\x01\x00')  # Suscribe to EmgData2Characteristic
        self.write_attr(0x35, b'\x01\x00')  # Suscribe to EmgData3Characteristic

        '''Bytes sent to handle 0x19 (command characteristic) have the following
        format: [command, payload_size, EMG mode, IMU mode, classifier mode]
        According to the Myo BLE specification, the commands are:
            0x01 -> set EMG and IMU
            0x03 -> 3 bytes of payload
            0x02 -> send 50Hz filtered signals
            0x01 -> send IMU data streams
            0x01 -> send classifier events
        '''
        self.write_attr(0x19, b'\x01\x03\x02\x01\x01')

        '''Sending this sequence for v1.0 firmware seems to enable both raw data and
        pose notifications.
        '''

        '''By writting a 0x0100 command to handle 0x28, some kind of "hidden" EMG
        notification characteristic is activated. This characteristic is not
        listed on the Myo services of the offical BLE specification from Thalmic
        Labs. Also, in the second line where we tell the Myo to enable EMG and
        IMU data streams and classifier events, the 0x01 command wich corresponds
        to the EMG mode is not listed on the myohw_emg_mode_t struct of the Myo
        BLE specification.
        These two lines, besides enabling the IMU and the classifier, enable the
        transmission of a stream of low-pass filtered EMG signals from the eight
        sensor pods of the Myo armband (the "hidden" mode I mentioned above).
        Instead of getting the raw EMG signals, we get rectified and smoothed
        signals, a measure of the amplitude of the EMG (which is useful to have
        a measure of muscle strength, but are not as useful as a truly raw signal).
        '''

        # self.write_attr(0x28, b'\x01\x00')  # Not needed for raw signals
        # self.write_attr(0x19, b'\x01\x03\x01\x01\x01')

    def mc_start_collection(self):
        '''Myo Connect sends this sequence (or a reordering) when starting data
        collection for v1.0 firmware; this enables raw data but disables arm and
        pose notifications.
        '''

        self.write_attr(0x28, b'\x01\x00')  # Suscribe to EMG notifications
        self.write_attr(0x1d, b'\x01\x00')  # Suscribe to IMU notifications
        self.write_attr(0x24, b'\x02\x00')  # Suscribe to classifier indications
        self.write_attr(0x19, b'\x01\x03\x01\x01\x01')  # Set EMG and IMU, payload size = 3, EMG on, IMU on, classifier on
        self.write_attr(0x28, b'\x01\x00')  # Suscribe to EMG notifications
        self.write_attr(0x1d, b'\x01\x00')  # Suscribe to IMU notifications
        self.write_attr(0x19, b'\x09\x01\x01\x00\x00')  # Set sleep mode, payload size = 1, never go to sleep, don't know, don't know
        self.write_attr(0x1d, b'\x01\x00')  # Suscribe to IMU notifications
        self.write_attr(0x19, b'\x01\x03\x00\x01\x00')  # Set EMG and IMU, payload size = 3, EMG off, IMU on, classifier off
        self.write_attr(0x28, b'\x01\x00')  # Suscribe to EMG notifications
        self.write_attr(0x1d, b'\x01\x00')  # Suscribe to IMU notifications
        self.write_attr(0x19, b'\x01\x03\x01\x01\x00')  # Set EMG and IMU, payload size = 3, EMG on, IMU on, classifier off

    def mc_end_collection(self):
        '''Myo Connect sends this sequence (or a reordering) when ending data collection
        for v1.0 firmware; this reenables arm and pose notifications, but
        doesn't disable raw data.
        '''

        self.write_attr(0x28, b'\x01\x00')
        self.write_attr(0x1d, b'\x01\x00')
        self.write_attr(0x24, b'\x02\x00')
        self.write_attr(0x19, b'\x01\x03\x01\x01\x01')
        self.write_attr(0x19, b'\x09\x01\x00\x00\x00')
        self.write_attr(0x1d, b'\x01\x00')
        self.write_attr(0x24, b'\x02\x00')
        self.write_attr(0x19, b'\x01\x03\x00\x01\x01')
        self.write_attr(0x28, b'\x01\x00')
        self.write_attr(0x1d, b'\x01\x00')
        self.write_attr(0x24, b'\x02\x00')
        self.write_attr(0x19, b'\x01\x03\x01\x01\x01')

    def vibrate(self, length):
        if length in xrange(1, 4):
            ## first byte tells it to vibrate; purpose of second byte is unknown
            self.write_attr(0x19, pack('3B', 3, 1, length))


    def add_emg_handler(self, h):
        self.emg_handlers.append(h)

    def add_imu_handler(self, h):
        self.imu_handlers.append(h)

    def add_pose_handler(self, h):
        self.pose_handlers.append(h)

    def add_arm_handler(self, h):
        self.arm_handlers.append(h)


    def on_emg(self, emg, moving):
        for h in self.emg_handlers:
            h(emg, moving)

    def on_imu(self, quat, acc, gyro):
        for h in self.imu_handlers:
            h(quat, acc, gyro)

    def on_pose(self, p):
        for h in self.pose_handlers:
            h(p)

    def on_arm(self, arm, xdir):
        for h in self.arm_handlers:
            h(arm, xdir)


if __name__ == '__main__':
    try:
        import pygame
        from pygame.locals import *
        HAVE_PYGAME = True
    except ImportError:
        HAVE_PYGAME = False

    if HAVE_PYGAME:
        w, h = 1200, 400
        scr = pygame.display.set_mode((w, h))

    last_vals = None
    with open('data/raw_emg.csv', mode='w+') as emg_file,  \
        open('data/raw_imu.csv', mode='w+') as imu_file,   \
        open('data/pose.csv',mode='w+') as pose_file:
        emg_writer = csv.writer(emg_file, delimiter=',')
        imu_writer = csv.writer(imu_file, delimiter=',')
        pose_writer = csv.writer(pose_file, delimiter=',')

        def plot(scr, vals):
            DRAW_LINES = True

            global last_vals
            if last_vals is None:
                last_vals = vals
                return

            D = 5
            scr.scroll(-D)
            scr.fill((0,0,0), (w - D, 0, w, h))
            for i, (u, v) in enumerate(zip(last_vals, vals)):
                if DRAW_LINES:
                    pygame.draw.line(scr, (0,255,0),
                                    (w - D, int(h/8 * (i+1 - u))),
                                    (w, int(h/8 * (i+1 - v))))
                    pygame.draw.line(scr, (255,255,255),
                                    (w - D, int(h/8 * (i+1))),
                                    (w, int(h/8 * (i+1))))
                else:
                    c = int(255 * max(0, min(1, v)))
                    scr.fill((c, c, c), (w - D, i * h / 8, D, (i + 1) * h / 8 - i * h / 8))

            pygame.display.flip()
            last_vals = vals

        m = MyoRaw(sys.argv[1] if len(sys.argv) >= 2 else None)

        def proc_emg(emg, moving, times=[]):
            if HAVE_PYGAME:
                ## update pygame display
                plot(scr, [e / 500. for e in emg])

                emg_writer.writerow([time.time(), *emg])
                
                pygame.event.pump()
            else:
                print(emg)

            ## print framerate of received data
            times.append(time.time())
            if len(times) > 20:
                #print((len(times) - 1) / (times[-1] - times[0]))
                times.pop(0)
        
        def proc_imu(quat, acc, gyro):
            if HAVE_PYGAME:
                imu_writer.writerow([time.time(), *quat, *acc, *gyro])
                pygame.event.pump()
            else:
                print(quat)


        m.add_emg_handler(proc_emg)    
        # m.add_pose_handler(lambda p: pose_writer.writerow((time.time(), p.name, p.value)))
        m.add_pose_handler(lambda p: print(time.time(), p.name, p.value))
        m.add_imu_handler(proc_imu)

        m.connect()

        m.add_arm_handler(lambda arm, xdir: print('arm', arm, 'xdir', xdir))

        m.add_pose_handler(lambda p: print('pose', p))
        
        # m.add_imu_handler(lambda quat, acc, gyro: imu_writer.writerow(quat + acc + gyro))
        # m.add_imu_handler(proc_imu)

        try:
            while True:
                if m.run(1) is None:
                    print("Connection lost, try to reconnect")
                    m.connect()
                else:
                    if HAVE_PYGAME:
                        for ev in pygame.event.get():
                            if ev.type == QUIT or (ev.type == KEYDOWN and ev.unicode == 'q'):
                                raise KeyboardInterrupt()
                            elif ev.type == KEYDOWN:
                                if K_1 <= ev.key <= K_3:
                                    m.vibrate(ev.key - K_0)
                                if K_KP1 <= ev.key <= K_KP3:
                                    m.vibrate(ev.key - K_KP0)

        except KeyboardInterrupt:
            pass
        finally:
            m.disconnect()
            emg_file.close()
            imu_file.close()
            pose_file.close()
            print()