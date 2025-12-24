Development
===========

Prerequisites
-------------

You will need:

-  `node`_
-  `Python 3`_
-  `Poetry`_

1. Clone the repo
-----------------

If you’re doing development work, you need access to the source code

.. code:: bash

   git clone https://github.com/MultiQC/UltraQC/

2. Install Dependencies
------------------------------------------------

You should install UltraQC using Poetry. You also need to install UltraQC and all its dependencies there:

.. code:: bash

   cd UltraQC
   poetry install

3. Install poetry shell
------------------------------------------------

You need to use poetry shell before running UltraQC.

.. code:: bash

   poetry shell

4. Enable development mode:
---------------------------

Setting this bash variable runs UltraQC in development mode. This means
that it will show full Python exception tracebacks in the web browser as
well as additional Flask plugins which help with debugging and
performance testing.

.. code:: bash

   export FLASK_DEBUG=1

5. Set up the database
----------------------

Running this command creates an empty SQLite UltraQC database file in the
installation directory called ``ultraqc.db``

.. code:: bash

   ultraqc initdb

6. Start ultraqc
---------------

Start UltraQC.

.. code:: bash

   ultraqc run

You will have to run the rest of these commands **in another terminal
window**, because ``ultraqc run`` blocks the terminal.

7. Setup your access key
------------------------

-  Login to UltraQC in your browser by browsing to
   http://localhost:5000/register/ (the port might differ, it will
   depend on what was output in the ``ultraqc run`` stage previously
-  Once registered, visit http://localhost:5000/users/multiqc_config and
   follow the instructions there to configure your access token in
   ``~/.multiqc_config.yaml``.
-  Note: if you you’d rather not pollute your home directory, you can
   instead name the file ``multiqc_config.yaml`` and place it in the
   current (UltraQC) directory. However, you will then have to run
   ``ultraqc upload`` from that directory each time

8. Load test data
-----------------

In order to develop new features you need some data to test it with:

.. code:: bash

   git clone https://github.com/TMiguelT/1000gFastqc
   for report in $(find 1000gFastqc -name '*.json')
       do ultraqc upload $report
   done

9. Install the JavaScript and start compiling
---------------------------------------------

This command will run until you cancel it, but will ensure that any
changes to the JavaScript are compiled instantly:

.. code:: bash

   npm install
   npm run watch

10. Install the pre-commit hooks
-------------------------------

UltraQC has a number of `pre-commit`_ hooks installed, which
automatically format and check your code before you commit.
To set it up, run:

.. code:: bash

   pre-commit install

From now on, whenever you commit, each changed file will get processed
by the pre-commit hooks. If a file is changed by this process (because
your code style didn’t match the configuration), you’ll have to
``git add`` the files again, and then re-run ``git commit``.
If it lets you write a commit message then everything has succeeded.

Next Steps
----------

You should now have a fully functional UltraQC test server running,
accessible on your localhost at http://127.0.0.1:5000

.. _node: https://nodejs.org/en/download/
.. _Python 3: https://www.python.org/downloads/
.. _pre-commit: https://pre-commit.com/
.. _Poetry: https://python-poetry.org/docs#installation
