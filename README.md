# Notes for Train and Test Long-term Myo sEMG
* Sonia Yuxiao Lai
* MSR Final Project  
&nbsp;
* Original by [Ulysse Côté-Allard](https://github.com/UlysseCoteAllard/LongTermEMG)
* Dataset recorded by [Suguru Kanoga](https://github.com/Suguru55/Wearable_Sensor_Long-term_sEMG_Dataset)


### Overview
The goal of this project is to determine whether [Unsupervised Transfer Learning proposed by Ulysse Côté-Allard](https://ieeexplore.ieee.org/document/9207910) is feasible for a low-end wearable sensor, such as Myo armband, which has 8 channels sampled at 200Hz. This repository contains a complete code for using my [Long-term EMG Myo library](https://github.com/aonai/long_term_EMG_myo) and results for training Suguru Kanoga's dataset using Ulysse Côté-Allard's algorithm across wearing locations, subjects, and days. 

### Usage
Running the code will store weights of Temporal-Spatial Descriptors (TSD) or Convolutional Network (ConvNet), Domain-Adversarial Neural Network (DANN), and Self-Calibrating Asynchronous Domain Adversarial Neural Network (SCADANN) models as well as corresponding testing results in txt and csv formats. See notes inside files for more details. 

### List of Files 
* `/collect_data`: code for reading EMG and IMU signals from a myo armband, and displaying the results.
    * `myo_raw.py`: code for recording EMD and IMU sigals into csv files
    * `plot_emg_diff_pos.ipynb`: results of recorded data
* `/test_data`: code for training TSD, DANN, and SCADANN on long-term Myo dataset. Also save accuracy results to csv files.
    * `myo_result_ConvNet_vs_TSD.ipynb`: compare performance of SCADANN between when the base model is ConvNet and TSD.  
    * `myo_result_across_days_loc0.ipyb`,  `myo_result_across_days_loc1.ipyb`,  `myo_result_across_days_loc2.ipyb`: train models using across days among the same subject at when wearing Myo at neutral position, inward rotation, and outward rotation respectively 
    * `myo_result_across_loc.ipynb`: train models across wearing locationss. This includes the default training options.  
    * `myo_result_across_sub_start0.ipynb`, `myo_result_across_sub_start1.ipynb`, `myo_result_across_sub_start2.ipynb`,`myo_result_across_sub_start3.ipynb`,`myo_result_across_sub_start4.ipynb`: train models using myo across subjects when the base model is trained using data recorded for subject_0, 1, 2, 3, 4 respectively. 
    * `test_on_myo_lower_freq.ipynb`: check whether lower frequency affect performance of TSD feature extraction functions
    * `check_mean_std_acc.ipynb`: calculates mean and standard deviation of accuracies for all cases. 
    * Others are notes for learning the models. Details can be found in documentation of [long term training python code](https://github.com/aonai/long_term_EMG_myo). 
