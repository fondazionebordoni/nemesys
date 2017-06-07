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

        pip install -r requirements-dev.txt

#. We use a version generated from git, so after doing a clone or pull you should always do

        cd common
        python version.py

#. Run the tests::

        paver test_all

   You should see output similar to this::

      $ paver test_all
      ---> pavement.test_all
      No style errors
      ============================================================================================================= test session starts =============================================================================================================
      platform linux2 -- Python 2.7.12 -- pytest-2.5.1
      collected 41 items

      tests/test_checkhost.py ...
      tests/test_exceptions.py ........
      tests/test_fakefile.py ...
      tests/test_getconf.py .
      tests/test_measure.py ..
      tests/test_mist_measure.py ..
      tests/test_netstat.py ........
      tests/test_profiler.py ....
      tests/test_task.py ..........

      ========================================================================================================== 41 passed in 1.00 seconds ==========================================================================================================
        ___  _   ___ ___ ___ ___
       | _ \/_\ / __/ __| __|   \
       |  _/ _ \\__ \__ \ _|| |) |
       |_|/_/ \_\___/___/___|___/



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

For now we only support Python 2.7

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
