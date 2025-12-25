UltraQC Usage: Setup
===================

Submitting data
---------------

Before you can do anything useful in UltraQC, you need to submit some
data to the database. You can do this by configuring and running MultiQC,
or by sending data directly via the API from any source.

MultiQC configuration
~~~~~~~~~~~~~~~~~~~~~

MultiQC needs a couple of configuration variables to know how to send
data to UltraQC. To find these, log into UltraQC and use the navigation
dropdown to get to the *MultiQC Configuration* page. Copy the specified
text into ``~/.multiqc_config.yaml``.

Note that this ``ultraqc_access_token`` is specific to your UltraQC user,
so shouldn’t be shared (it’s effectively a password). All data uploaded
using that token will be attributed to your user.

Running MultiQC
~~~~~~~~~~~~~~~

Once configured, run MultiQC as you would normally. You should see a
couple of additional log messages under the ``ultraqc`` namespace as
follows:

::

   $ multiqc .

   [INFO   ]         multiqc : This is MultiQC v1.3
   [INFO   ]         multiqc : Template    : default
   [INFO   ]         multiqc : Searching './'
   Searching 63 files..  [####################################]  100%
   [INFO   ]  feature_counts : Found 6 reports
   [INFO   ]            star : Found 6 reports
   [INFO   ]        cutadapt : Found 6 reports
   [INFO   ]    fastq_screen : Found 6 reports
   [INFO   ]          fastqc : Found 6 reports
   [INFO   ]         multiqc : Compressing plot data
   [INFO   ]          ultraqc : Sending data to UltraQC
   [INFO   ]          ultraqc : Data upload successful
   [INFO   ]         multiqc : Report      : multiqc_report.html
   [INFO   ]         multiqc : Data        : multiqc_data
   [INFO   ]         multiqc : MultiQC complete

**NB: You need MultiQC v1.3 or later for UltraQC integration to work.**

Submitting non-MultiQC data
~~~~~~~~~~~~~~~~~~~~~~~~~~~

UltraQC can also accept QC data from any source via its REST API.
See the main README for details on the JSON format and API endpoints.

Example using curl:

::

   curl -X POST http://localhost:8000/api/upload_data \
     -H "Content-Type: application/json" \
     -H "access_token: YOUR_TOKEN" \
     -d '{"report_saved_raw_data": {"multiqc_custom": {"sample1": {"metric": 0.95}}}}'
