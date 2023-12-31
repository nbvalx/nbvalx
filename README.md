# nbvalx

**nbvalx** is a collection of `pytest` utils built on top of `nbval`.

**nbvalx** is currently developed and maintained at [Università Cattolica del Sacro Cuore](https://www.unicatt.it/) by [Dr. Francesco Ballarin](https://www.francescoballarin.it).

**nbvalx** can be `pip install`ed from [its GitHub repository](https://github.com/multiphenics/nbvalx/) or from [PyPI](https://pypi.org/project/nbvalx/)

## Cell magics for conditional running based on tags
Add a cell with
```
%load_ext nbvalx
```
at the beginning of a notebook to load **nbvalx** `IPython` extension. The extension is implemented in [`nbvalx/jupyter_magics.py`](https://github.com/multiphenics/nbvalx/blob/main/nbvalx/jupyter_magics.py).

The extension allows to register a list of allowed tags
```
%register_run_if_allowed_tags tag1, tag2
```
and set the current value of the tag with
```
%register_run_if_current_tag tag1
```

The tag can then be used to conditionally run cells. As an example, if the subsequent two cells were
```
%%run_if tag1
current_tag = "tag1"
```
```
%%run_if tag2
current_tag = "tag2"
```
the first cell would never be executed, and the second cell would assign the value `"tag2"` to `current_tag`.

See [`tests/notebooks/data/tags`](https://github.com/multiphenics/nbvalx/blob/main/tests/notebooks/data/tags) for a few simple notebooks using tags.

## Custom pytest hooks for jupyter notebooks

The file [`nbvalx/pytest_hooks_notebooks.py`](https://github.com/multiphenics/nbvalx/blob/main/nbvalx/pytest_hooks_notebooks.py) contains a few utility functions to be used in pytest configuration file for notebooks tests.
The `pytest` hooks which can be customized in this way are:
* `pytest_addoption`,
* `pytest_collect_file`,
* `pytest_runtest_makereport`,
* `pytest_runtest_setup`,
* `pytest_runtest_teardown`, and
* `pytest_sessionstart`.

For clarity, the hooks implemented in [`nbvalx/pytest_hooks_notebooks.py`](https://github.com/multiphenics/nbvalx/blob/main/nbvalx/pytest_hooks_notebooks.py) do not have a `pytest_` prefix, as it will be the user's responsability to pick them up and assign them to the corresponding `pytest` hook in a custom `conftest.py`, as show in [`tests/notebooks/conftest.py`](https://github.com/multiphenics/nbvalx/blob/main/tests/notebooks/conftest.py).

The hooks change the default behavior of `nbval` in the following ways:
1. the options `--nbval` and `--nbval-lax`, which `nbval` requires to pass explicitly, are here enabled implicitly;
2. support for `MPI` run by providing the `--np` option to `pytest`. When running `pytest --np 2`, **nbvalx** will start a `ipyparallel.Cluster` and run notebooks tests in parallel on 2 cores. In the default case one core is employed, and an `ipyparallel.Cluster` is not started;
3. support for tags, as introduced in the previous section, as governed by two flags:
    * `--tag-collapse`: if enabled (default), strip all cells for which the `%%run_if` condition does not evaluate to `True`. This may be used to prepare notebook files to be read by the end user, as stripping unused cells may improve the readability of the notebook. If not enabled, all cells will be kept.
    * `--ipynb-action`: either `collect-notebooks` (default) or `create-notebook`. Both actions create several copies of the original notebook that differ by the currently enabled tag. For instance, if the original notebook in the section above is called `notebook.ipynb` and has two allowed tags, the action will generate a file `notebook[tag1].ipynb` where `tag1` is assigned as the current value of the tag, and a file `notebook[tag2].ipynb` where `tag2` is assigned as the current value of the tag. If `tag-collapse` is enabled, cells associated to all remaining tags are stripped. The `create-notebook` action only generates the tagged notebooks; instead, the `collect-notebooks` additionally also runs them through `pytest`;
4. support for collecting cell outputs to log files, which are saved in a work directory provided by the user with the argument `--work-dir`. This is helpful to debug failures while testing notebooks. If no work directory is specified, the default value is `f".ipynb_pytest/np_{np}/collapse_{tag_collapse}"`;
5. the notebook is treated as if it were a demo or tutorial, rather than a collection of unit tests in different cells. For this reason, if a cell fails, the next cells will be skipped;
6. a new `# PYTEST_XFAIL` marker is introduced to mark cells as expected to fail. The marker must be the first entry of the cell. A similar marker `# PYTEST_XFAIL_AND_SKIP_NEXT` marks the cell as expected to fail and interrupts execution of the subsequent cells.

## Custom pytest hooks for unit tests

The file [`nbvalx/pytest_unit_tests.py`](https://github.com/multiphenics/nbvalx/blob/main/nbvalx/pytest_unit_tests.py) contains a few utility functions to be used in pytest configuration file for notebooks tests.
The `pytest` hooks which can be customized in this way are:
* `pytest_runtest_setup`, and
* `pytest_runtest_teardown`.

For clarity, the hooks implemented in [`nbvalx/pytest_unit_tests.py`](https://github.com/multiphenics/nbvalx/blob/main/nbvalx/pytest_hooks_notebooks.py) do not have a `pytest_` prefix, as it will be the user's responsability to pick them up and assign them to the corresponding `pytest` hook in a custom `conftest.py`, as show in [`tests/unit/conftest.py`](https://github.com/multiphenics/nbvalx/blob/main/tests/unit/conftest.py).

The hooks are typically employed to obtain a `MPI`-parallel safe execution of python unit tests by calling garbage collection and putting a `MPI` barrier after each test.

## Custom pytest hooks for unit tests
The file [`nbvalx/tempfile.py`](https://github.com/multiphenics/nbvalx/blob/main/nbvalx/tempfile.py) contains `MPI` parallel-safe context managers to create temporary files and directories. Similarly to the `tempfile` module in the standard library, the following context managers are provided:
* `nbvalx.tempfile.TemporaryDirectory`,
* `nbvalx.tempfile.TemporaryFile`.
