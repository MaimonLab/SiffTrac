# Analysis for ROS file logs 


## ROS Logs

These are for direct access to the various log files and types.
They do minimal processing and analysis, just provide a shared
interface and syntax so that new types of data can easily be
slotted into existing classes.
## ROS Interpreters



## Experiments

An `Experiment` class attempts to locate _all_ log files in
a directory (or near a directory) and collate them together,
storing their respective `ROSInterpreter` classes.