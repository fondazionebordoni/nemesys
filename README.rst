==============
NeMeSys Client
==============

This project has been remodeled partially using the template by `Travis CI <https://travis-ci.org/seanfisk/python-project-template>`_.

It is a client that will measure the upload, download and ping performance of the italian Internet providers. More information can be found on the `official page <https://www.misurainternet.it/>`_.


Project Setup
=============

The project is not intended to be used from the code, but packaged for each platform (Mac OS, Windows and Linux). In order to use these packages, the user must register `here <https://www.misurainternet.it/>`_.

The setup.py cannot be used for installing the package, it is currently only used for various settings.


Instructions
------------

Here are some instructions to test or run parts of the project


#. Clone the project::

        git clone https://github.com/fondazionebordoni/nemesys nemesys
        cd nemesys

#. *(Optional, but good practice)* Create a new virtual environment:

   With pyenv_ and pyenv-virtualenv_::

       pyenv virtualenv nemesys
       pyenv local nemesys

   With virtualenvwrapper_::

       mkvirtualenv nemesys

   With plain virtualenv_::

       virtualenv /path/to/nemesys-venv
       source /path/to/nemesys-venv/bin/activate

   If you are new to virtual environments, please see the `Virtual Environment section`_ of Kenneth Reitz's Python Guide.

#. Install the project's development and runtime requirements::

        pip install -r requirements.txt
        pip install python-daemon==2.1.2
        pip install paver flake8 pytest

#. We use a version generated from git, so after doing a clone or pull you should always do

        python -m common.version

#. Run the tests::

    Note that one of the tests checks the absence of WiFi connections, and fails if a WiFi connection is active. 
    It is therefore recommended to disable WiFi before running the tests.

        paver test

   You should see output similar to this::

      $ paver test
    >   pavement.test
    =================== test session starts ===================
        platform linux2 -- Python 3.8.10, pytest-4.6.11, py-1.11.0, pluggy-0.13.1
        rootdir: /home/test/nemesys
        collected 54 items

        tests/test_backend_response.py ......                [ 11%]
        tests/test_checkhost.py ....                         [ 20%]
        tests/test_exceptions.py .........                   [ 37%]
        tests/test_fakefile.py ....                          [ 44%]
        tests/test_measure.py ..                             [ 48%]
        tests/test_mist_measure.py ..                        [ 51%]
        tests/test_netstat.py ........                       [ 66%]
        tests/test_profiler.py .....                         [ 75%]
        tests/test_task.py .............                     [100%]

        ========================================================================================================== 41 passed in 1.00 seconds ==========================================================================================================
        ___  _   ___ ___ ___ ___
        | _ \/_\ / __/ __| __|   \
        |  _/ _ \\__ \__ \ _|| |) |
        |_|/_/ \_\___/___/___|___/


    Also available is the `paver test_all` command which, in addition to unit tests, runs the linter to analyze the quality of the code.

Using Paver
-----------

The ``pavement.py`` file comes with a number of tasks already set up for you. You can see a full list by typing ``paver help`` in the project root directory. The following are included::

    Tasks from pavement:
    lint             - Perform PEP8 style check, run PyFlakes, and run McCabe complexity metrics on the code.
    doc_open         - Build the HTML docs and open them in a web browser.
    coverage         - Run tests and show test coverage report.
    doc_watch        - Watch for changes in the Sphinx documentation and rebuild when changed.
    test             - Run the unit tests.
    get_tasks        - Get all paver-defined tasks.
    commit           - Commit only if all the tests pass.
    test_all         - Perform a style check and run all unit tests.

For example, to run the both the unit tests and lint, run the following in the project root directory::

    paver test_all

To build the HTML documentation, then open it in a web browser::

    paver doc_open


Supported Python Versions
=========================

Python 3.8 and 3.10

Licenses
========

The license for the code which makes up this Python project can be found in the file LICENSE.

We also use a number of other pieces of software, whose licenses are listed here for convenience.

+------------------------+----------------------------------+
|Project                 |License                           |
+========================+==================================+
|Python itself           |Python Software Foundation License|
+------------------------+----------------------------------+
|argparse (now in stdlib)|Python Software Foundation License|
+------------------------+----------------------------------+
|Paver                   |Modified BSD License              |
+------------------------+----------------------------------+
|colorama                |Modified BSD License              |
+------------------------+----------------------------------+
|flake8                  |MIT/X11 License                   |
+------------------------+----------------------------------+
|mock                    |Modified BSD License              |
+------------------------+----------------------------------+
|pytest                  |MIT/X11 License                   |
+------------------------+----------------------------------+

Issues
======

Please report any bugs or requests that you have using the GitHub issue tracker! You can also file a question or issue through the helpdesk `here <https://www.misurainternet.it/supporto/>`_.

Authors
=======

Through the years there have been several authors in this project. The most recent/current authors are

* Elin Wedlund
* Giuseppe Pantanetti
