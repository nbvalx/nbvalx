# nbvalx

**nbvalx** is a collection of `pytest` utils built on top of `nbval`.

**nbvalx** is currently developed and maintained at [Università Cattolica del Sacro Cuore](https://www.unicatt.it/) by [Prof. Francesco Ballarin](https://www.francescoballarin.it).

**nbvalx** can be `pip install`ed from [its GitHub repository](https://github.com/nbvalx/nbvalx/) or from [PyPI](https://pypi.org/project/nbvalx/)

## Cell magics

Add a cell with
```
%load_ext nbvalx
```
at the beginning of a notebook to load **nbvalx** `IPython` extension. The extension is implemented in [`nbvalx/jupyter_magics.py`](https://github.com/nbvalx/nbvalx/blob/main/nbvalx/jupyter_magics.py).

### Cell magics for conditional running based on tags

The extension enables registering a list of tags, and their allowed values
```
%%register_allowed_run_if_tags
bool_tag: True, False
int_tag: 2, 10
string_tag: "value1", "value2"
```
and set the current value of each tag with
```
%%register_current_run_if_tags
bool_tag = False
int_tag = 10
string_tag = "value1"
```

The tags can then be used to conditionally run cells. As an example, if the subsequent two cells were
```
%%run_if bool_tag and int_tag > 5
print("Cell with float and integer comparison")
```
```
%%run_if string_tag == "value1"
print("Cell with string comparison")
```
the string `"Cell with float and integer comparison"` would never get printed, while the `"Cell with string comparison"` would indeed be printed.

Without **nbvalx**, the four cells above could have equivalently been written as
```
bool_tag = False
int_tag = 10
string_tag = "value1"
if bool_tag and int_tag > 5:
    print("Cell with float and integer comparison")
if string_tag == "value1":
    print("Cell with string comparison")
```
The plain formulation is certainly less verbose and more compact than **nbvalx** equivalent one with four cells. However, it is less "testing-friendly", because the values of `bool_tag`, `int_tag` and `string_tag` are hardcoded in the notebook and cannot be easily varied.

A similar statement can be used as an HTML comment in markdown cells
```
<!-- keep_if string_tag == "value1" -->
This is a markdown cell which explains a code cell that will be run only if string_tag == "value1".
```
Markdown cells will be stripped only when running through `pytest` with the `--collapse` option, see below.

### Cell magics for parametrized python variables

The extension enables registering a list of parameters, and their allowed values
```
%%register_allowed_parameters
bool_parameter: True, False
int_parameter: 2, 10
string_parameter: "value1", "value2"
```
and set the current value of each parameter with
```
%%register_current_parameters
bool_parameter = False
int_parameter = 10
string_parameter = "value1"
```

The parameters can then be used as standard python variables in the notebook. As an example, if the subsequent cell were
```
if bool_parameter and int_parameter > 5:
    print("Cell with float and integer comparison")
if string_parameter == "value1":
    print("Cell with string comparison")
```
the string `"Cell with float and integer comparison"` would never get printed, while the `"Cell with string comparison"` would indeed be printed.

### The difference between tags and parameters

With a `pytest` terminology, both **nbvalx** tags and parameters correspond to defining a sort of parametrization of the notebook.

A **nbvalx** parameter takes an allowed list of values and a current value, and defines the current value as python variable that is available for use in the code of the notebook. This is the closest concept to the parametrization typically employed in `pytest`, which defines a python variable as well.
Tags instead do not define a python variable visible in the notebook, but just an identifier with scope limited to the `%%run_if ...` magic.

As an alternative, `papermill` defines an implementation of parameter similar to the one in **nbvalx**, but it does not provide a tag.

See [`tests/notebooks/data/magic_entries`](https://github.com/nbvalx/nbvalx/blob/main/tests/notebooks/data/magic_entries) for a few simple notebooks using tags and parameters.

## Custom pytest hooks for jupyter notebooks

The file [`nbvalx/pytest_hooks_notebooks.py`](https://github.com/nbvalx/nbvalx/blob/main/nbvalx/pytest_hooks_notebooks.py) contains a few utility functions to be used in pytest configuration file for notebooks tests.
The `pytest` hooks which can be customized in this way are:
* `pytest_addoption`,
* `pytest_collect_file`, and
* `pytest_sessionstart`.

For clarity, the hooks implemented in [`nbvalx/pytest_hooks_notebooks.py`](https://github.com/nbvalx/nbvalx/blob/main/nbvalx/pytest_hooks_notebooks.py) do not have a `pytest_` prefix, as it will be the user's responsability to pick them up and assign them to the corresponding `pytest` hook in a custom `conftest.py`, as show in [`tests/notebooks/conftest.py`](https://github.com/nbvalx/nbvalx/blob/main/tests/notebooks/conftest.py).

The hooks change the default behavior of `nbval` in the following ways:
1. the options `--nbval` and `--nbval-lax`, which `nbval` requires to pass explicitly, are here enabled implicitly;
2. support for `MPI` run by providing the `--np` option to `pytest`. When running `pytest --np 2`, **nbvalx** will start a `ipyparallel.Cluster` and run notebooks tests in parallel on 2 cores. In the default case one core is employed, and an `ipyparallel.Cluster` is not started;
3. support for cell magics, as introduced in the previous section, as governed by two flags:
    * `--collapse`: if enabled (default), strip all cells with configuration of cell magics, namely `%load_ext`, `%%register_allowed_run_if_tags`, `%%register_allowed_parameters`, then use the current tag values to strip cells for which the `%%run_if ...` or `<!-- keep_if ... -->` conditions do not evaluate to `True`. The current parameter values are left available as python variables. This flag may be used to prepare notebook files to be read by the end user, as stripping cells disabled by the current tag values may improve the readability of the notebook. If not enabled, all cells will be kept.
    * `--ipynb-action`: either `collect-notebooks` (default) or `create-notebook`. Both actions create several copies of the original notebook that differ by the currently enabled cell magics. For instance, if the original notebook in the section above is called `notebook.ipynb` and has a tag called `tag` with two allowed values `value1` and `value2`, the action will generate a file `notebook[tag=value1].ipynb` in which `value1` is assigned as the current value of `tag` (replacing the default value), and another file `notebook[tag2].ipynb` in which `value2` is assigned as the current value of `tag` (replacing the default). If `collapse` is enabled, cells associated to all remaining cell magics are stripped. The `create-notebook` action only generates the postprocessed notebooks; instead, the `collect-notebooks` additionally also runs them through `pytest`;
4. support for collecting cell outputs to log files, which are saved in a work directory provided by the user with the argument `--work-dir`. This is helpful to debug failures while testing notebooks. Log files are of two formats: a text log, with extension `.log` when running without `--np` or `.log-{rank}` when running in parallel; a notebook log, with extension `.log.ipynb`. If no work directory is specified, the default value is `f".ipynb_pytest/np_{np}/collapse_{collapse}"`. In case the notebook depends on additonal data files (e.g., local python modules), the flag `--link-data-in-work-dir` can be passed with glob patterns of data files that need to be symbolically linked in the work directory. The option can be passed multiple times in case multiple patterns are desired, and they will be joined with an or condition;
5. the notebook is treated as if it were a demo or tutorial, rather than a collection of unit tests in different cells. For this reason, if a cell fails, the next cells will be skipped;
6. a new `# PYTEST_XFAIL` marker is introduced to mark cells as expected to fail. The marker must be the first entry of the cell. A similar marker `# PYTEST_XFAIL_AND_SKIP_NEXT` marks the cell as expected to fail and interrupts execution of the subsequent cells. Both previous markers have a variant with `XFAIL_IN_PARALLEL` instead of `XFAIL`, that consider the cell to be expected to fail only when the value provided to `--np` is greater than one;
7. support for running notebooks through `coverage` without having to install the `pyvtest-cov` plugin. Use flag `--coverage-source` to set the module name for which coverage testing is requested.

## Custom pytest hooks for unit tests

The file [`nbvalx/pytest_unit_tests.py`](https://github.com/nbvalx/nbvalx/blob/main/nbvalx/pytest_unit_tests.py) contains a few utility functions to be used in pytest configuration file for notebooks tests.
The `pytest` hooks which can be customized in this way are:
* `pytest_runtest_setup`, and
* `pytest_runtest_teardown`.

For clarity, the hooks implemented in [`nbvalx/pytest_unit_tests.py`](https://github.com/nbvalx/nbvalx/blob/main/nbvalx/pytest_hooks_notebooks.py) do not have a `pytest_` prefix, as it will be the user's responsability to pick them up and assign them to the corresponding `pytest` hook in a custom `conftest.py`, as show in [`tests/unit/conftest.py`](https://github.com/nbvalx/nbvalx/blob/main/tests/unit/conftest.py).

The hooks are typically employed to obtain a `MPI`-parallel safe execution of python unit tests by calling garbage collection and putting a `MPI` barrier after each test.

## MPI parallel-safe temporary files and directories
The file [`nbvalx/tempfile.py`](https://github.com/nbvalx/nbvalx/blob/main/nbvalx/tempfile.py) contains `MPI` parallel-safe context managers to create temporary files and directories. Similarly to the `tempfile` module in the standard library, the following context managers are provided:
* `nbvalx.tempfile.TemporaryDirectory`,
* `nbvalx.tempfile.TemporaryFile`.
