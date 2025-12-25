Changelog
=========

UltraQC 2.0.0 (Development)
---------------------------

This is a major release that modernizes the entire codebase, migrating from Flask to FastAPI.

Breaking Changes
~~~~~~~~~~~~~~~~

-  **Flask to FastAPI migration**: The entire web framework has been replaced
-  **New authentication**: JWT token-based authentication replaces Flask-Login
-  **Async database**: SQLAlchemy 2.0 with async support
-  **Environment variables**: Configuration now uses ``ULTRAQC_*`` prefix instead of ``MEGAQC_*``
-  **Python 3.9+**: Minimum Python version is now 3.9

New Features
~~~~~~~~~~~~

-  **FastAPI backend**: High-performance async API with automatic OpenAPI docs
-  **Modern dark theme**: Sci-fi neon aesthetics with improved UI
-  **Version from GitHub**: Version is automatically fetched from latest GitHub release
-  **Improved API docs**: Swagger UI at ``/docs`` and ReDoc at ``/redoc``
-  **Non-MultiQC data support**: Documentation for sending custom QC data

Internal Changes
~~~~~~~~~~~~~~~~

-  Complete rewrite of authentication system using JWT tokens
-  Migrated from Flask-SQLAlchemy to SQLAlchemy 2.0 with async support
-  Updated all dependencies to modern versions
-  Improved test suite with async test support

---

Legacy Changelog (from MegaQC)
==============================

The following changelog entries are from the original MegaQC project before
the fork to UltraQC.

0.3.0
-----

.. _breaking-changes-1:

Breaking Changes
~~~~~~~~~~~~~~~~

-  `[#138]`_ Added ``USER_REGISTRATION_APPROVAL`` as a config variable,
   which defaults to true. This means that the admin must explicitly
   activate new users in the user management page
   (``/users/admin/users``) before they can login. To disable this
   feature, you need to create a config file (for example
   ``ultraqc.conf.yaml``) with the contents:

   .. code:: yaml

      STRICT_REGISTRATION: false

   Then, whenever you run UltraQC, you need to ``export MEGAQC_CONFIG
   /path/to/ultraqc.conf.yaml``

-  Much stricter REST API permissions. You now need an API token for
   almost all requests. One exception is creating a new account, which
   you can do without a token, but it will be deactivated by default,
   unless it is the first account created

-  Dropped support for Node 8

.. _new-features-1:

New Features
~~~~~~~~~~~~

-  `[#140]`_ Added a changelog. It’s here! You’re reading it!
-  Sphinx based documentation on Github Pages
-  `[#69]`_ Added a check to verify that a database exists and exit nicely if not


.. _bug-fixes-1:

Bug Fixes
~~~~~~~~~

- `[#139]`_ Fixed the user management page (``/users/admin/users``), which lost its JavaScript
- `[#148]`_ Explicitly disable pagination for ``find()`` calls, ensuring we get more than 30 results in certain places
- `[#156]`_ Fixed comparison plot running into comparisons with None values
- `[#170]`_ Improved handling of environment variables with environs
- `[#194]`_ Forward more headers through nginx when using Docker Compose. This should avoid bad HTTP redirects.

.. _internal-changes-1:

Internal Changes
~~~~~~~~~~~~~~~~

-  Tests for the REST API permissions
-  Enforce inactive users (by default) in the model layer
-  Many and more dependency updates


.. _[#69]:  https://github.com/MultiQC/MegaQC/issues/69
.. _[#138]: https://github.com/MultiQC/MegaQC/issues/138
.. _[#139]: https://github.com/MultiQC/MegaQC/issues/139
.. _[#140]: https://github.com/MultiQC/MegaQC/issues/140
.. _[#148]: https://github.com/MultiQC/MegaQC/issues/148
.. _[#156]: https://github.com/MultiQC/MegaQC/issues/156
.. _[#170]: https://github.com/MultiQC/MegaQC/issues/170
.. _[#194]: https://github.com/MultiQC/MegaQC/issues/194
