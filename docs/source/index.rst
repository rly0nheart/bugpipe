Bugpipe
==========

Unofficial Python client for Buganizer; the Google Issue Tracking system.


Quick Start
-----------

.. code-block:: bash

   bugpipe search "status:open"


.. code-block:: python

   from bugpipe import Bugpipe


   with Bugpipe() as client:
       result = client.search(query="status:open priority:p1", page_size=25)
       for issue in result.issues:
           print(f"#{issue.id} [{issue.status.name}] {issue.title}")


.. toctree::
   :hidden:

   installation
   usage
   api
   audit
