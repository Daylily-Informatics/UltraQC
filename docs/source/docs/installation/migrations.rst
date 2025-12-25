Migrations
==========

Introduction
------------

Migrations are updates to a database schema. This is relevant if, for
example, you set up a UltraQC database (using ``initdb``), and then a new
version of UltraQC is released that needs new tables or columns.

When to migrate
---------------

Every time a new version of UltraQC is released, you should ensure your
database is up to date. You don’t need to run the migrations the first
time you install UltraQC, because the ``ultraqc initdb`` command replaces
the need for migrations.

How to migrate
--------------

To migrate, run the following commands:

.. code:: bash

   cd ultraqc
   alembic upgrade head

Note: when you run these migrations, you **must** have the same
environment as you use to run UltraQC normally, which means the same
value of ``ULTRAQC_DATABASE_URL`` environment variable. Otherwise it
will migrate the wrong database (or a non-existing one).

Stamping your database
----------------------

The complete migration history has only recently been added. This means
that, if you were using UltraQC in the past when migrations were not
included in the repo, your database won’t know what version you’re currently at.

To fix this, first you need to work out which migration your database is
up to. Browse through the files in ``ultraqc/migrations/versions``,
starting from the oldest date (at the top of each file), until you find
a change that wasn’t present in your database. At this point, note the
``revision`` value at the top of the file, (e.g. ``revision = "007c354223ec"``).

Next, run the following command, replacing ``<revision ID>`` with the
revision you noted above:

.. code:: bash

   alembic stamp <revision ID>
