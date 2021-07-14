# Notes for long_term_EMG_myo
* msr final project 
* Sonia Yuxiao Lai

### List of Files 
* `/collect_data`: code for reading EMG and IMU signals from a myo armband, and displaying the results.
    * `myo_raw.py`: code for recording EMD and IMU sigals into csv files
    * `plot_emg_diff_pos.ipynb`: results of recorded data
* `/test_data`: code for training TSD, DANN, and SCADANN on 3DC and myo dataset. Also save accuracy results to csv files.
    * `LongTerm_3DC.ipynb`: train models using 3DC dataset and their results
    * `myo_result.ipynb`: train models using myo dataset and their results across sessions
    * `myo_result_across_sub.ipynb`: train models using myo dataset and their results across subjects 
    * `myo_result_across_days_loc0.ipyb`,  `myo_result_across_days_loc1.ipyb`,  `myo_result_across_days_loc2.ipyb`: train models using myo dataset and their results across days among the same subject and same wearing location.  
    * `test_on_myo_lower_freq.ipynb`: check whether lower frequency affect performance of TSD feature extraction functions
    * `check_mean_std_acc.ipynb`: calculates mean and standard deviation of accuracies for all cases. 
    * Others are notes for learning the models. Details can be found in documentation of [long term training python code](https://github.com/aonai/long_term_EMG_myo). 
