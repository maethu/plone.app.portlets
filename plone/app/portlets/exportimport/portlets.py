from zope.interface import implements
from zope.interface import Interface
from zope.interface import directlyProvides
from zope.interface import providedBy

from zope.component import adapts
from zope.component import getSiteManager
from zope.component import getUtilitiesFor
from zope.component.interfaces import IComponentRegistry

from Products.GenericSetup.interfaces import IBody
from Products.GenericSetup.interfaces import ISetupEnviron

from Products.GenericSetup.utils import XMLAdapterBase
from Products.GenericSetup.utils import exportObjects
from Products.GenericSetup.utils import importObjects
from Products.GenericSetup.utils import _getDottedName
from Products.GenericSetup.utils import _resolveDottedName

from plone.portlets.interfaces import IPortletType
from plone.portlets.interfaces import IPortletManager

from plone.portlets.constants import USER_CATEGORY, GROUP_CATEGORY, CONTENT_TYPE_CATEGORY

from plone.portlets.manager import PortletManager
from plone.portlets.storage import PortletCategoryMapping
from plone.portlets.registration import PortletType

class PortletsXMLAdapter(XMLAdapterBase):
    """In- and exporter for a local portlet configuration
    """
    implements(IBody)
    adapts(IComponentRegistry, ISetupEnviron)
    
    name = 'portlets'
    _LOGGER_ID = 'portlets'
    
    def _exportNode(self):
        # hack around an issue where _getObjectNode expects to have the context
        # a meta_type, which isn't the case for a component registry
        if IComponentRegistry.providedBy(self.context):
            self.context.meta_type = 'ComponentRegistry'
        node = self._getObjectNode('portlets')
        if IComponentRegistry.providedBy(self.context):
            del(self.context.meta_type)
        node.appendChild(self._extractPortlets())
        self._logger.info('Portlets exported')
        return node

    def _importNode(self, node):
        self._initProvider(node)
        self._logger.info('Portlets imported')

    def _initProvider(self, node):
        if self.environ.shouldPurge():
            self._purgePortlets()
        self._initPortlets(node)

    def _purgePortlets(self):
        registeredPortletTypes = [r.name for r in self.context.registeredUtilities()
                                        if r.provided == IPortletType]
                                    
        for name, portletType in getUtilitiesFor(IPortletType):
            if name in registeredPortletTypes:
                self.context.unregisterUtility(provided=IPortletType, name=name)
        
        portletManagerRegistrations = [r for r in self.context.registeredUtilities()
                                        if r.provided.isOrExtends(IPortletManager)]
        
        for registration in portletManagerRegistrations:
            self.context.unregisterUtility(provided=registration.provided,
                                           name=registration.name)

    def _initPortlets(self, node):
        registeredPortletTypes = [r.name for r in self.context.registeredUtilities()
                                    if r.provided == IPortletType]
                                        
        registeredPortletManagers = [r.name for r in self.context.registeredUtilities()
                                        if r.provided.isOrExtends(IPortletManager)]
        
        for child in node.childNodes:
            if child.nodeName.lower() == 'portletmanager':
                manager = PortletManager()
                name = str(child.getAttribute('name'))
                
                managerType = child.getAttribute('type')
                if managerType:
                    directlyProvides(manager, _resolveDottedName(managerType))
                
                manager[USER_CATEGORY] = PortletCategoryMapping()
                manager[GROUP_CATEGORY] = PortletCategoryMapping()
                manager[CONTENT_TYPE_CATEGORY] = PortletCategoryMapping()
                
                if name not in registeredPortletManagers:
                    self.context.registerUtility(component=manager,
                                                 provided=IPortletManager,
                                                 name=name)
                                                 
            elif child.nodeName.lower() == 'portlet':
                addview = str(child.getAttribute('addview'))
                if addview not in registeredPortletTypes:
                    portlet = PortletType()
                    portlet.title = str(child.getAttribute('title'))
                    portlet.description = str(child.getAttribute('description'))
                    portlet.addview = addview
                    
                    for_ = child.getAttribute('for')
                    if for_:
                        portlet.for_ = _resolveDottedName(str(for_))

                    self.context.registerUtility(component=portlet, 
                                                 provided=IPortletType, 
                                                 name=addview)
    
    def _extractPortlets(self):
        fragment = self._doc.createDocumentFragment()
        
        registeredPortletTypes = [r.name for r in self.context.registeredUtilities()
                                            if r.provided == IPortletType]
        portletManagerRegistrations = [r for r in self.context.registeredUtilities()
                                            if r.provided.isOrExtends(IPortletManager)]
        
        for r in portletManagerRegistrations:
            child = self._doc.createElement('portletmanager')
            child.setAttribute('name', r.name)

            specificInterface = providedBy(r.component).flattened().next()
            if specificInterface != IPortletManager:
                child.setAttribute('type', _getDottedName(specificInterface))
            
            fragment.appendChild(child)
            
        for name, portletType in getUtilitiesFor(IPortletType):
            if name in registeredPortletTypes:
                child = self._doc.createElement('portlet')
                child.setAttribute('addview', portletType.addview)
                child.setAttribute('title', portletType.title)
                child.setAttribute('description', portletType.description)
                
                if portletType.for_:
                    child.setAttribute('for', _getDottedName(portletType.for_))

        return fragment

def dummyGetId():
    return ''

def importPortlets(context):
    """Import portlet managers and portlets
    """
    sm = getSiteManager(context.getSite())
    if sm is None or not IComponentRegistry.providedBy(sm):
        logger = context.getLogger('portlets')
        logger.info("Can not register components - no site manager found.")
        return
        
    # XXX GenericSetup.utils.importObjects expects the object to have a getId
    # function. We provide a dummy one for now, but this should be fixed in GS
    # itself
    sm.getId = dummyGetId
    importObjects(sm, '', context)
    del(sm.getId)

def exportPortlets(context):
    """Export portlet managers and portlets
    """
    sm = getSiteManager(context.getSite())
    if sm is None or not IComponentRegistry.providedBy(sm):
        logger = context.getLogger('portlets')
        logger.info("Nothing to export.")
        return
        
    # XXX GenericSetup.utils.exportObjects expects the object to have a getId
    # function. We provide a dummy one for now, but this should be fixed in GS
    # itself
    sm.getId = dummyGetId
    exportObjects(sm, '', context)
    del(sm.getId)