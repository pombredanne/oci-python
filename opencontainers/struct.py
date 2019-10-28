
# Copyright (C) 2019-2020 Vanessa Sochat.

# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

from opencontainers.logger import bot
import copy
import json


class StructAttr(object):
    '''A struct attribute holds a name, jsonName, value, attribute type,
       and if it's required or not. The name should hold the parameter name
       as reflected in the original (usually GoLang) implementation, while
       the jsonName is how it should be serialized to json.

       Parameters
       ==========
       name: the name (key) for the attribute
       attType: the attribute type (a python type), can be provided in list
       required: boolean if required or not
       jsonName: the name to serialize to json (not required, will use name)
       value: optionally, provide a value on init
       omitempty: if true, don't serialize with response.       
    '''
    def __init__(self, name, attType, required, 
                       jsonName=None, value=None, omitempty=True):
        self.name = name
        self.value = value
        self.attType = attType
        self.required = required
        self.jsonName = jsonName or name
        self.omitempty = omitempty

    def __str__(self):
        return "<opencontainers.struct.StructAttr-%s:%s>" %(self.name, self.value)

    def __repr__(self):
        return self.__str__()

    def set(self, value):
        '''set a new value, and validate the type. Return true if set
        '''
        if self.validate_type(value):
            self.value = value
            return True
        return False


    def validate_type(self, value):
        '''ensure that an attribute is of the correct type. If we are given
           a list as type, then the value within it is the type we are checking.
        '''
        # If it's a list with something inside
        if isinstance(self.attType, list):

            # If value not a list, invalid
            if not isinstance(value, list):
                return False

            # A type to check is inside
            if self.attType:
                attType = self.attType[0]

                for entry in value:
                    if not isinstance(entry, attType):
                        return False

        # Otherwise, validate as is
        else:
            if not isinstance(value, self.attType):
                return False
        return True


class Struct(object):
    '''a Struct is a general base class that allows for printing 
       and validating a set of attributes according to their defined subclass.
       the subclass should have an init function that uses the functions
       here to add required attributes.
    '''
    attrs = {}

    def newAttr(self, name, attType, required=False, jsonName=None, omitempty=True):
        '''add a new attribute, including a name, json key to dump,
           type, and if required. We don't need a value here

           Parameters
           ==========
           name: the name (key) for the attribute
           attType: the attribute type (a python type), can be provided in list
           required: boolean if required or not
           jsonName: the name to serialize to json (not required, will use name)
           omitempty: if true, don't serialize with response.
        '''
        if name in self.attrs:
            bot.exit("%s has already been added." % name)
        self.attrs[name] = StructAttr(name=name, 
                                      attType=attType,
                                      required=required,
                                      jsonName=jsonName, 
                                      omitempty=omitempty)

    def _clear_values(self):
        '''if a load is done, we remove previously loaded values for any
           attributes
        '''
        for name, att in self.attrs.items():
            self.attrs[name].value = None        


    def to_dict(self):
        '''return a Struct as a dictionary, must be valid
        '''
        # A lookup of "empty" values based on types (mirrors Go)
        lookup = {str: "", int: None, list: [], dict: {}}

        if self.validate():      
            result = {}
            for name, att in self.attrs.items():
                if not att.value and att.omitempty:
                    continue
                if not att.value:
                    value = lookup.get(att.attType, [])
                    result[att.jsonName] = value            
                else:
                    result[att.jsonName] = att.value
            return result

    def to_json(self):
        '''get the dictionary of a struct and return pretty printed json
        '''
        result = self.to_dict()
        if result:
            result = json.dumps(result, indent=4)
        return result


    def add(self, name, value):
        '''add a value to an existing attribute, normally when used by a client
        '''
        if name not in self.attrs:
            bot.exit("%s is not a valid attribute." % name)

        attr = self.attrs[name]

        # Don't validate the type if provided is empty
        if value:
            if not attr.set(value):
                bot.exit("%s must be type %s." %(name, attr.attType))


    def load(self, content):
        '''given a dictionary load into its respective object
        '''
        if not isinstance(content, dict):
            bot.exit("Please provide a dictionary to load.")

        # Validate the content, only clear if it's valid
        attrs = copy.deepcopy(self.attrs)

        # Look up attributes based on jsonKey
        lookup = self.generate_json_lookup()

        # Go through each value for the content, validate
        for key, value in content.items():
            att = lookup.get(key)
            if not att:
                bot.exit("%s is not a valid json attribute." % key)

        # If we get here, all parameters are valid, replace
        self._clear_values()
        for key, value in content.items():
            att = lookup.get(key)
            att.set(value)


    def generate_json_lookup(self):
        '''based on the attributes, generate a jsonName lookup object.
           keys are jsonNames we find in the wild, names are attribute names.
        '''
        lookup = dict()
        for name, att in self.attrs.items():
            lookup[att.jsonName] = att
        return lookup


    def validate(self):
        '''validate goes through each attribute, and ensure that it is of the
           correct type, and if required it is defined. This is already done
           to some extent when add is called.
        '''
        for name, att in self.attrs.items():

            # A required attribute cannot be None or empty
            if att.required and not att.value:
                bot.error('%s is required.' % name)
                return False

            # The attribute must match its type
            if not isinstance(att.value, att.attType):
                bot.error("%s should be type %s" %(name, att.attType))
                return False

        return True