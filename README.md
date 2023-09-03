# SIFFTRAC

The SiffPy interface for FicTrac data that can be aligned to siff data

The central class is the `Experiment`. Usually, you generate `Experiment`s
automatically by passing a directory containing all the relevant logs and
data. The `Experiment` will then attempt to parse the files in that directory
and all its subdirectories to discern what types of data they contain, and then
provide programmatic access to those data.



- TODO: POLARS!

## Experiment

## ROS data analysis

The data from our ROS-based experimental setup produces many filetypes,
almost all with the same extensions, and often with unpredictable filenames
(i.e. we may change the convention for inclusion of specific strings in the
name of the file, at the tail, or where it's stored relative to other files).
But they follow some templated styles, and the actual contents of the file
almost always reveal exactly what it contains. So this set of experimental
analysis tools is designed to 1) investigate a file quickly to determine what
type of data it contains, 2) figure out if it's relevant to an experiment or
set of experiments of interest, and 3) provide simple access to the data
underneath (ideally without dealing with a bunch of `DataFrame` objects or
other abstractions that get in the way). For every type of ROS output, there
is a `ROSInterpreter` subclass, which supplies a few basic pieces of information
about the type of data contained, and then lets the `ROSInterpreter` framework
take care of the rest. Various ROS nodes share certain features that are convenient,
(e.g. defined timepoints that allow you to see when the experiment took place,
are specified with a "config file", store informatino about the git commit that
these data come from), but not all nodes share all of those features, so they
are implemented in mixins stored in `sifftrac.ros.interpreters.mixins`.

The `ROSInterpreter` superclass asks that you specify a `LOG_TAG`, a class
attribute that describes the suffix of the filetypes your ROS node produces,
and an accompanying `ROSLog` class that can parse data of that type. You
also should implement a method `isvalid(cls, file_path : PathLike, report_failure : bool)->bool` that can determine with as little time and overhead as possible whether
a file located at `file_path` is valid for this class / log.