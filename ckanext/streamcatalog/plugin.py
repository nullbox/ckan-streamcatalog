import ckan.plugins as p
import ckan.plugins.toolkit as toolkit

# activity.py - rewritten core functionality replaces dataset with datastream.
#from ckanext.streamcatalog.activity import user_activity_list_html, package_activity_list_html, group_activity_list_html, \
#                                           organization_activity_list_html, recently_changed_packages_activity_list_html
from ckanext.streamcatalog.activity import dashboard_activity_stream

''' Helper functions that can be called from CKAN snippet. '''

def getAllSubscriptions(package_id = None, user_id = None):
    ''' Returns all "New Resource" activities and most relevant related objects (Activity, ActivityDetail, User and Resource). '''
    import ckan.model as model
    
    # Form a query, which selects all "New Resource" activities and most relevant related objects.
    q = model.Session.query(model.User, model.Resource) \
             .join(model.Activity, model.Activity.user_id==model.User.id) \
             .join(model.ActivityDetail, model.ActivityDetail.activity_id==model.Activity.id) \
             .join(model.Resource, model.ActivityDetail.object_id==model.Resource.id)
    if package_id:
        q = q.filter(model.Activity.object_id == package_id)
    if user_id:
        q = q.filter(model.Activity.user_id == user_id)
    q = q.filter(model.ActivityDetail.object_type == 'Resource')
    q = q.filter(model.ActivityDetail.activity_type == 'new')
    
    # Execute the query and return all results from it.
    return q.all()

def countSubscriptions(subscriptions, state = 'active'):

    subscription_count = 0

    for subscription in subscriptions:
        if subscription.Resource.state == state:
            subscription_count = subscription_count + 1

    return subscription_count

''' The extension plugin. '''

class StreamCatalogPlugin(p.SingletonPlugin):
    ''' This is a plugin that transforms datasets into datastreams and resources as subscriptions to those datastreams. '''
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IRoutes, inherit=True)

    def before_map(self, map):
        # New views. Note the inclusion of an extra parameter, which enables native menu item linking.
        map.connect('ckanadmin_wso2esb', '/ckan-admin/wso2esb', controller='ckanext.streamcatalog.controllers.admin_controller:admin', action='wso2esb')
        
        # WSO2 ESB related redirects.
        map.connect('/dataset/new_resource/{id}', controller='ckanext.streamcatalog.controllers.package_controller:package', action='new_resource')
        map.connect('/dataset/{id}/resource_delete/{resource_id}', controller='ckanext.streamcatalog.controllers.package_controller:package', action='resource_delete')
        map.connect('/dataset/{id}/publish', controller='ckanext.streamcatalog.controllers.package_controller:package', action='publish')
        # WSO2 ESB functionality.
        map.connect('/wso2esb/topicsubscription_delete/{subscription_id}', controller='ckanext.streamcatalog.controllers.wso2esb_controller:WSO2ESB', action='topicsubscription_delete')
        map.connect('/wso2esb/topicsubscription_create', controller='ckanext.streamcatalog.controllers.wso2esb_controller:WSO2ESB', action='topicsubscription_create')
        # Activity stream rewrites.
        map.connect('/dataset/activity/{id}', controller='ckanext.streamcatalog.controllers.package_controller:package', action='activity')
        map.connect('/group/activity/{id}/{offset}', controller='ckanext.streamcatalog.controllers.group_controller:group', action='activity')
        map.connect('/organization/activity/{id}', controller='ckanext.streamcatalog.controllers.organization_controller:organization', action='activity')

        return map

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        # 'templates' is the path to the templates dir, relative to this
        # plugin.py file.
        toolkit.add_template_directory(config, 'templates')

    def get_helpers(self):
        ''' Register template helper functions. '''

        # Template helper function names should begin with the name of the
        # extension they belong to, to avoid clashing with functions from
        # other extensions.
        return {
                'streamcatalog_getAllSubscriptions': getAllSubscriptions,
                'streamcatalog_countSubscriptions': countSubscriptions,
                # activity.py - rewritten core functionality replaces dataset with datastream.
                #'streamcatalog_user_activity_list_html': user_activity_list_html,
                #'streamcatalog_package_activity_list_html': package_activity_list_html,
                #'streamcatalog_group_activity_list_html': group_activity_list_html,
                #'streamcatalog_organization_activity_list_html': organization_activity_list_html,
                #'streamcatalog_recently_changed_packages_activity_list_html': recently_changed_packages_activity_list_html,
                #
                'streamcatalog_dashboard_activity_stream': dashboard_activity_stream
            }