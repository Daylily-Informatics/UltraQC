Development
===========

Prerequisites
-------------

You will need:

-  `node`_
-  `Python 3.9+`_
-  `pip`_ (or `Poetry`_ for advanced users)

1. Clone the repo
-----------------

If you’re doing development work, you need access to the source code

.. code:: bash

   git clone https://github.com/Daylily-Informatics/UltraQC.git

2. Install Dependencies
-----------------------

You can install UltraQC using pip with development dependencies:

.. code:: bash

   cd UltraQC
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"

Or using Poetry:

.. code:: bash

   cd UltraQC
   poetry install
   poetry shell

3. Enable development mode
--------------------------

Setting this environment variable runs UltraQC in development mode with
auto-reload and detailed error messages:

.. code:: bash

   export ULTRAQC_DEBUG=true

4. Set up the database
----------------------

Running this command creates an empty SQLite UltraQC database file in the
installation directory called ``ultraqc.db``

.. code:: bash

   ultraqc initdb

5. Start UltraQC
----------------

Start UltraQC with auto-reload for development:

.. code:: bash

   ultraqc run --reload

You will have to run the rest of these commands **in another terminal
window**, because ``ultraqc run`` blocks the terminal.

6. Setup your access key
------------------------

-  Open UltraQC in your browser at http://localhost:8000/register/
-  Register a new account (the first user becomes admin)
-  Once registered, visit http://localhost:8000/users/multiqc_config and
   follow the instructions there to configure your access token in
   ``~/.multiqc_config.yaml``.
-  Note: if you you’d rather not pollute your home directory, you can
   instead name the file ``multiqc_config.yaml`` and place it in the
   current (UltraQC) directory. However, you will then have to run
   ``ultraqc upload`` from that directory each time

7. Load test data
-----------------

In order to develop new features you need some data to test it with:

.. code:: bash

   git clone https://github.com/TMiguelT/1000gFastqc
   for report in $(find 1000gFastqc -name '*.json')
       do ultraqc upload $report
   done

8. Install the JavaScript and start compiling
---------------------------------------------

This command will run until you cancel it, but will ensure that any
changes to the JavaScript are compiled instantly:

.. code:: bash

   npm install
   npm run watch

9. Install the pre-commit hooks
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

API Documentation
-----------------

Once running, you can access the auto-generated API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Next Steps
----------

You should now have a fully functional UltraQC test server running,
accessible on your localhost at http://127.0.0.1:8000

.. _node: https://nodejs.org/en/download/
.. _Python 3.9+: https://www.python.org/downloads/
.. _pip: https://pip.pypa.io/en/stable/
.. _pre-commit: https://pre-commit.com/
.. _Poetry: https://python-poetry.org/docs#installation
