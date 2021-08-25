# Notes for Train and Test Long-term Myo sEMG
* Sonia Yuxiao Lai
* MSR Final Project  
&nbsp;
* Original by [Ulysse Côté-Allard](https://github.com/UlysseCoteAllard/LongTermEMG)
* Dataset recorded by [Suguru Kanoga](https://github.com/Suguru55/Wearable_Sensor_Long-term_sEMG_Dataset)


### Overview
The goal of this project is to determine whether [Unsupervised Transfer Learning proposed by Ulysse Côté-Allard](https://ieeexplore.ieee.org/document/9207910) is feasible for a low-end wearable sensor, such as Myo armband, which has 8 channels sampled at 200Hz. This repository contains a complete code for using my [Long-term EMG Myo library](https://github.com/aonai/long_term_EMG_myo) and results for training Suguru Kanoga's dataset using Ulysse Côté-Allard's algorithm across days, wearing locations, and subjects. 

### Usage
Running the code will store weights of Temporal-Spatial Descriptors (TSD) or Convolutional Network (ConvNet), Domain-Adversarial Neural Network (DANN), and Self-Calibrating Asynchronous Domain Adversarial Neural Network (SCADANN) models as well as corresponding testing results in txt and csv formats. See notes inside files for more details. 

### List of Files 
* `/collect_data`: code for reading EMG and IMU signals from a myo armband, and displaying the results.
    * `myo_raw.py`: code for recording EMD and IMU signals into csv files
    * `plot_emg_diff_pos.ipynb`: results of recorded data
* `/test_data`: code for training TSD, DANN, and SCADANN on long-term Myo dataset. Also display and save accuracy results to csv files.
    * `check_mean_std_acc.ipynb`: calculates mean and standard deviation of accuracies increasements from TSD to SCADANN for all cases. 
    * `myo_result_ConvNet_vs_TSD.ipynb`: compare performance of SCADANN between when the base model is ConvNet and TSD.  
    * `myo_result_across_days_loc0.ipyb`,  `myo_result_across_days_loc1.ipyb`,  `myo_result_across_days_loc2.ipyb`: train models using across days among the same subject at when wearing Myo at neutral position, inward rotation, and outward rotation respectively 
    * `myo_result_across_loc.ipynb`: train models across wearing locations. This includes the default training options.  
    * `myo_result_across_sub_start0.ipynb`, `myo_result_across_sub_start1.ipynb`, `myo_result_across_sub_start2.ipynb`,`myo_result_across_sub_start3.ipynb`,`myo_result_across_sub_start4.ipynb`: train models across subjects when the base model is trained using data recorded for subject 0, 1, 2, 3, 4 respectively. 
    * `test_on_myo_lower_freq.ipynb`: check whether lower frequency affect performance of TSD feature extraction functions. 

### Results
##### 1. Train Across Days
The overall accuracy increases from 66% to 74%, 67% to 76%, and 67% to 75% when models are on the same subject at neutral location, inward rotation, and outward rotation respectively.   
The increasing trend from TSD to SCADANN does not always exist. When training for subject 0 on day 1 and 2 at neutral location, accuracies decrease by 2.2% and 1.2% respectively. Looking closely at the gestures accuracies in the same case, some gestures are not recognizable by the model (e.g. accuracy of gesture 4 for subject 0 at day 2 remains to be 0.0 for TSD, DANN, and SCADANN). One reason for this may be that the dataset is not sufficient for training a robust model. The total number of trials per wearing location is 40. If distributing these trials among 10 days, each day will only include 4 trials. This means that the model is receiving a worse dataset than in other cases. Regardless, SCADANN proves to have a better performance when all tests are considered.
##### 2. Train Across Locations
The overall accuracy increases from 72% to 79%. This accuracy is generally better than in other cases. Considering all the results, it has less effect than other controlling factors such as different subjects and across days on a long term.
##### 3. Train Across Subjects
The overall accuracy increases from 54% to 63%, 51% to 59%, 49% to 58%, from 49% to 60%, and from 52% to 60% when models are trained based on subject 0 to 4 respectively. In most cases, if the TSD model trained based on one subject is good at predicting gestures of others, then so does its SCADANN model. 
##### 4. Conclusion
SCADANN can improve accuracy in classifying gestures recorded by low-end and low-frequency wearable sensors. To optimize the final performance of the model, the first base model should be trained using a good algorithm and a good dataset. That is, the algorithm should be suitable for training predicting gestures from sEMG signals, and the dataset should include enough amount of recording trails.