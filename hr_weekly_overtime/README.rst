Weekly Overtime
===============

This module allows to calculate the salary of an employee paid with hourly
rates based on a weekly overtime policy.


Configuration
=============

Create a weekly overtime policy.
This can be set on two different levels: the contract or the company.

Go to the company form, in the configuration tab.
In the field Weekly Overtime Policy, create a new record.

Example: the company pays 1.5x the normal hourly rate for
each hour after 40. After 50 hours, it is paid 2x the normal rate.

In this case, you would enter 2 policy lines:

Lower Limit: 40, Upper Limit: 50, Rate: 150
Lower Limit: 50, Upper Limit: Empty, Rate: 200


Usage
=====

Complete a payslip for an employee or in batch. Compute the payslip(s) as usual.


Credits
=======

Contributors
------------

.. image:: http://sflx.ca/logo
   :alt: Savoir-faire Linux
   :target: http://sflx.ca

* David Dufresne <david.dufresne@savoirfairelinux.com>

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.