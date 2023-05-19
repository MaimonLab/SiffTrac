# Analysis for ROS file logs 

Many types of ROS logs share some features, with each types' overlaps
varying between them. So most of these features are implemented as
mixins, and the ROS logs that have those features inherit from the
corresponding mixin class. This gives them a shared set of attribute
names, calling conventions, etc. Node-specific functionality, for
example unit conversions, complex properties, data transforms,
are implemented by the individual interpreters.

## ROS Logs

These are for direct access to the various log files and types.
They do minimal processing and analysis, just provide a shared
interface and syntax so that new types of data can easily be
slotted into existing classes.
## ROS Interpreters

These are meant to process and transform the data in its corresponding
`ROSLog` subclass. They inherit from the various mixins to process the
data files upon loading, and implement computational functionality (
unit conversions, data analysis, etc.)

## Experiments

An `Experiment` class attempts to locate _all_ log files in
a directory (or near a directory) and collate them together,
storing their respective `ROSInterpreter` classes.