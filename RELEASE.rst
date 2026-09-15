Versioning
~~~~~~~~~~

To create a new release simply tag a commit on the main branch. Once that tag
is pushed, the `test-and-package.yaml
<https://github.com/PEEC-Nature-Youth-Group/pumaguard/blob/main/.github/workflows/test-and-package.yaml>`__
workflow will create a new release and attach the build artifacts, i.e. the
Python wheel and the snap, to the release.

Our version convention is to use only the major (semantic) version with a
leading letter `v`, i.e.,

.. code-block::

    v42
