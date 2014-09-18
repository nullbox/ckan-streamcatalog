#!/usr/bin/python
# -*- coding: utf-8 -*-
from ckan.controllers.package import PackageController
from ckan.lib.base import *

import ckan.model as model
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.lib.navl.dictization_functions import DataError, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import get_action, check_access

from ckan.common import OrderedDict, _, json, request, c, g, response

from py4j.protocol import Py4JJavaError, Py4JError
import ckan.lib.base as base
abort = base.abort

from urllib import urlencode
import ckan.plugins as p
import ckan.lib.maintain as maintain
from ckan.controllers.package import _encode_params, url_with_params, search_url
from ckan.lib.helpers import _create_url_with_params


def getBrokerClient():
    ''' Gets BrokerClientWrapper java class to communicate with WSO2 ESB. '''

    from py4j.java_gateway import JavaGateway
    gateway = JavaGateway()
    return gateway.entry_point

def getPackageIdFromName(package_name):
    ''' Turn id (dataset's slug) to package_id (its actual id). '''
    
    package_data = get_action('package_show')({'model': model, 'session': model.Session, 'user': c.user or c.author, 'auth_user_obj': c.userobj}, {'id': package_name})
    if 'id' in package_data:
        return package_data['id']
    else:
        return None

def getResourceUrlName(resource_name):
    ''' Use resource id to get its url field value. '''

    resource_data = get_action('resource_show')({'model': model, 'session': model.Session, 'user': c.user or c.author, 'auth_user_obj': c.userobj}, {'id': resource_name})
    if 'url' in resource_data:
        return resource_data['url']
    else:
        return None

class package(PackageController):

    def new_resource(self, id, data=None, errors=None, error_summary=None):
        if request.method == 'POST' and not data:
            # Recogniced new resource form POST, extract variables.
            postdata = data or clean_dict(unflatten(tuplize_dict(parse_params(request.POST))))
            if 'save' in postdata and 'url' in postdata:
                package_id = getPackageIdFromName(id)
                # Add a new subscription for the topic named after the dataset, pointing to the URL given.
                brokerclient = getBrokerClient()
                try:
                    result = brokerclient.subscribe(package_id, postdata['url'])
                except Py4JJavaError, e:
                    error_message = str(e)
                    if 'Error While Subscribing :Cannot initialize URI with empty parameters.' in error_message:
                        error_message = _('Error While Subscribing: Cannot initialize URI with empty parameters.')
                    if 'org.apache.axis2.AxisFault: Connection refused' in error_message:
                        error_message = _('Error While Subscribing: Cannot connect to WSO2 ESB.')

                    if errors and isinstance(errors, dict):
                        errors.update({ 'error': error_message })
                    else:
                        errors = { 'error': error_message }
                    data = postdata
                    error_summary = { _('WSO2 ESB'): error_message }

        return super(package, self).new_resource(id, data, errors, error_summary)

    def resource_delete(self, id, resource_id):
        # Use a sneaky trick to gain access to the subscription id: attempt recreating the same subscription, which then returns its id.
        # @TODO Accessing subscription's id like this is potentially hazardous and redundant. Save the id to the resource's data instead.
        brokerclient = getBrokerClient()
        package_id = getPackageIdFromName(id)
        resource_url = getResourceUrlName(resource_id)
        subscription_id = brokerclient.subscribe(package_id, resource_url)
        # Since we now have access to the subscription id, simply use it to unsubscribe.
        # @TODO Try-catch
        brokerclient.unsubscribe(subscription_id)

        return super(package, self).resource_delete(id, resource_id)