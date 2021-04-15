Grid Synergy ecommerce fork
==============================

.. image:: https://img.shields.io/badge/hack.d-Lawrence%20McDaniel-orange.svg
     :target: https://lawrencemcdaniel.com
     :alt: Hack.d Lawrence McDaniel


Developers
----------

- open-release/* branches are locked. Do not attempt to push commits to any of these branches.
- gs/* branches are limited. You'll need to use pull requests. You should create your own personal feature branch, make your code commits to this branch, push these commits, and then create a pull request.

The default branch of this repo is gs/koa.master. You should create your feature branches from this branch, and you should rebase often.

.. code-block:: bash

  # Branch gs/koa.master was created as follows
  #   -------------------------------------------
  git checkout open-release/koa.master
  git checkout -b gs/koa-master
  git push --set-upstream origin gs/koa.master


  # This fork is sync'd to edx/edx-platform using the following pull/rebase procedure
  # 1.) pull any new commits from edx/edx-platform 
  # -------------------------------------------
  git checkout open-release/koa.master
  git pull
  git push

  # 2.) rebase gs/koa.master with these new commits
  # -------------------------------------------
  git checkout gs/koa.master
  git rebase open-release/koa.master
  git push


edX E-Commerce Service  |Travis|_ |Codecov|_
--------------------------------------------
.. |Travis| image:: https://travis-ci.com/edx/ecommerce.svg?branch=master
.. _Travis: https://travis-ci.com/edx/ecommerce

.. |Codecov| image:: http://codecov.io/github/edx/ecommerce/coverage.svg?branch=master
.. _Codecov: http://codecov.io/github/edx/ecommerce?branch=master

This repository contains the edX E-Commerce Service, which relies heavily on `django-oscar <https://django-oscar.readthedocs.org/en/latest/>`_, as well as all frontend and backend code used to manage edX's product catalog and handle orders for those products.

Documentation
-------------

`Documentation <https://edx-ecommerce.readthedocs.io/en/latest/>`_ is hosted on Read the Docs. The source is hosted in this repo's `docs <https://github.com/edx/ecommerce/tree/master/docs>`_ directory. To contribute, please open a PR against this repo.

License
-------

The code in this repository is licensed under version 3 of the AGPL unless otherwise noted. Please see the LICENSE_ file for details.

.. _LICENSE: https://github.com/edx/ecommerce/blob/master/LICENSE

How To Contribute
-----------------

Contributions are welcome. Please read `How To Contribute <https://github.com/edx/edx-platform/blob/master/CONTRIBUTING.rst>`_ for details. Even though it was written with ``edx-platform`` in mind, these guidelines should be followed for Open edX code in general.

Reporting Security Issues
-------------------------

Please do not report security issues in public. Please email security@edx.org.

Get Help
--------

Ask questions and discuss this project on `Slack <https://openedx.slack.com/messages/ecommerce/>`_ or in the `edx-code Google Group <https://groups.google.com/forum/#!forum/edx-code>`_.
