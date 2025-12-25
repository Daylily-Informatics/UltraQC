Docker
======

UltraQC offers two ways of getting a containerized setup running:

1. A single Docker container containing UltraQC with Uvicorn ASGI HTTP server
2. A Docker Compose stack containing the UltraQC container, a Postgres container and a NGINX container

.. _ultraqc_docker_container:

The UltraQC Docker container
--------------------------------

Overview
~~~~~~~~~~

The UltraQC container is based on the `Node container <https://hub.docker.com/_/node>`_
to compile all Javascript scripts and a Python container with Uvicorn
providing FastAPI and UltraQC preconfigured for production deployments.

Pulling the docker image from dockerhub
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run UltraQC with docker, simply use the following command:

.. code:: bash

   docker run -p 8000:8000 daylily/ultraqc

This will pull the latest image from `dockerhub`_ and run UltraQC on port 8000.

Note that you will need to publish the port in order to access it from
the host, or other machines. For more information, read https://docs.docker.com/engine/reference/run/ .

Building your own docker image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you prefer, you can build your own docker image if you have pulled the
UltraQC code from GitHub. Simply cd to the UltraQC root directory and run

.. code:: bash

   docker build . -t daylily/ultraqc

You can then run UltraQC as described above:

.. code:: bash

   docker run -p 8000:8000 daylily/ultraqc

Configuration
~~~~~~~~~~~~~~~

UltraQC uses Uvicorn as the ASGI server. You can customize the host, port,
and other settings via environment variables.

Environment variables
^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, the UltraQC related environment variables are set to:

.. code-block::

   ULTRAQC_SECRET="SuperSecretValueYouShouldReallyChange"
   ULTRAQC_DATABASE_URL="postgresql://ultraqc:ultraqcpswd@127.0.0.1:5432/ultraqc"
   ULTRAQC_HOST="0.0.0.0"
   ULTRAQC_PORT="8000"

To run UltraQC with custom environment variables use the ``-e key=value`` run options.
For more information, please read
`Docker - setting environment variables <https://docs.docker.com/engine/reference/commandline/run/#set-environment-variables--e---env---env-file>`_.
Running UltraQC for example with a custom database URL works as follows:

.. code-block:: bash

   docker run -e ULTRAQC_DATABASE_URL=postgresql://user:pass@host/db daylily/ultraqc

Furthermore, be aware that the default latest tag will typically be a development version
and may not be very stable. You can specify a tagged version to run a release instead:

.. code:: bash

   docker run -p 8000:8000 daylily/ultraqc:v2.0.0

Also note that docker will use a local version of the image if it
exists. To pull the latest version of UltraQC use the following command:

.. code:: bash

   docker pull daylily/ultraqc

Using persistent data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Dockerfile has been configured to automatically create persistent
volumes for the data and log directories. This volume will be created
without additional input by the user, but if you want to re-use those
volumes with a new container you must specify them when running the
docker image.

The easiest way to ensure the database persists between container states
is to always specify the same volume for ``/usr/local/lib/postgresql``.
If a volume is found with that name it is used, otherwise it creates a
new volume.

To create or re-use a docker volume named ``pg_data``:

.. code:: bash

   docker run -p 8000:8000 -v pg_data:/usr/local/lib/postgresql daylily/ultraqc

The same can be done for a log directory volume called ``pg_logs``

.. code:: bash

   docker run -p 8000:8000 -v pg_data:/usr/local/lib/postgresql -v pg_logs:/var/log/postgresql daylily/ultraqc

If you did not specify a volume name, docker will have given it a long
hex string as a unique name. If you do not use volumes frequently, you
can check the output from ``docker volume ls`` and
``docker volume inspect $VOLUME_NAME``. However, the easiest way is to
inspect the docker container.

.. code:: bash

   # ugly default docker output
   docker inspect --format '{{json .Mounts}}' example_container

   # use jq for pretty formatting
   docker inspect --format '{{json .Mounts}}' example_container | jq

   # or use python for pretty formatting
   docker inspect --format '{{json .Mounts}}' example_container | python -m json.tool

Example output for the above, nicely formatted:

.. code:: json

   [
   {
      "Type": "volume",
      "Name": "7c8c9dfbcc66874b472676659dde6a5c8e15dea756a620435c83f5980c21d804",
      "Source": "/var/lib/docker/volumes/7c8c9dfbcc66874b472676659dde6a5c8e15dea756a620435c83f5980c21d804/_data",
      "Destination": "/usr/local/lib/postgresql",
      "Driver": "local",
      "Mode": "",
      "RW": true,
      "Propagation": ""
   },
   {
      "Type": "volume",
      "Name": "6d48d24a660d078dfe4c04960aeb1848ea688a3eae0d4b7b54b1043f7885e428",
      "Source": "/var/lib/docker/volumes/6d48d24a660d078dfe4c04960aeb1848ea688a3eae0d4b7b54b1043f7885e428/_data",
      "Destination": "/var/log/postgresql",
      "Driver": "local",
      "Mode": "",
      "RW": true,
      "Propagation": ""
   }
   ]

Running UltraQC with a local Postgres database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To access a Postgres database running on a localhost you need to use
the host's networking. For more information, read
https://docs.docker.com/network/host/ .

An example command to run UltraQC with a Postgres database which is accessible
on ``localhost:5432``, looks as follows:

.. code:: bash

   docker run --network="host" daylily/ultraqc

Note that by default ``localhost=127.0.0.1``.

.. _docker_compose_stack:

The UltraQC Docker Compose stack
------------------------------------

Since a fully working and performant UltraQC instance depends on a SQL database
and a reverse proxy, UltraQC offers a docker-compose stack, which sets up three
containers for a zero configuration setup.

Overview
~~~~~~~~~~~

The `docker-compose`_ configuration can be accessed in the `deployment folder`_.
The docker-compose configuration provides the :ref:`ultraqc_docker_container`,
a `postgres container <https://hub.docker.com/_/postgres>`_ for the SQL database
and a `nginx container <https://hub.docker.com/_/nginx>`_ for the reverse proxy setup.

Usage
~~~~~~~~

Inside the `deployment folder`_ the `docker-compose`_ configuration
together with the associated `.env <https://github.com/Daylily-Informatics/UltraQC/blob/main/deployment/.env>`_ file
are found. To spin up all containers simply run from inside the `deployment folder <https://github.com/Daylily-Informatics/UltraQC/blob/main/deployment>`_:

.. code:: bash

   docker-compose up

All containers should now spin up and the UltraQC server should be accessible on ``0.0.0.0:80``.
Alternatively, you can spin up the containers in the background:

.. code:: bash

   docker-compose up -d

The ``-d`` option detaches from the containers, but will keep them running.

Configuration
~~~~~~~~~~~~~~~~

Environment variables
^^^^^^^^^^^^^^^^^^^^^^^^^^

The default environment variables for UltraQC used when starting the :ref:`ultraqc_docker_container`
are defined inside the `.env <https://github.com/Daylily-Informatics/UltraQC/blob/main/deployment/.env>`_ file.
Simply edit the file and the new environment variables will be passed to the :ref:`ultraqc_docker_container`.

Further runtime arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Further runtime arguments can be added to a
`command section <https://docs.docker.com/compose/compose-file/#command>`_
inside the `docker-compose`_ configuration file.

.. _deployment_folder: https://github.com/Daylily-Informatics/UltraQC/blob/main/deployment
.. _docker-compose: https://github.com/Daylily-Informatics/UltraQC/blob/main/deployment/docker-compose.yml
.. _dockerhub: https://hub.docker.com/r/daylily/ultraqc/

HTTPS
~~~~~
By default, the UltraQC stack ships with a self-signed SSL certificate for testing purposes.
For this reason we recommend that you use HTTP to access the stack.
However, if you want to enable HTTPS, perhaps because you are making UltraQC available on the public internet, then it should be simple to install your own certificates.
To do so, go to the ``deployment`` directory and edit the ``.env`` file.
Then, edit these lines to the full filepath of the respective ``.crt`` and ``.key`` files:

.. code::

    CRT_PATH=./nginx-selfsigned.crt
    KEY_PATH=./nginx-selfsigned.key

After this, run the stack as described above, and then you should be able to access UltraQC on ``https://your_hostname``.
