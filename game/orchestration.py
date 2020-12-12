#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

'''
Orchestration of game in a dungeon room
'''


import sys
import math
import time
import uuid
import random
import logging

import game.layer
import game.level
import game.heroes
import game.steers
import game.objects
from game.common import DOORS, KEYS, AVAILABLE_OBJECT_IDS, EMPTY_TILE, NULL_TILE,\
    IDENTIFIER, X, Y, LIFE, SCORE, OBJECT_CLASS, OBJECT_TYPE, STATE,\
    POINTS_PER_DOOR, POINTS_PER_KEY, POINTS_PER_LEVEL
from game.pyxeltools import TILE_SIZE


def _closest_(target, objects=None):
    if not objects:
        return None
    current_distance = sys.float_info.max
    closest = None
    for candidate in objects:
        distance = math.sqrt(
            (target.x - target.x) ** 2 + (target.y - candidate.y) ** 2
        )
        if distance < current_distance:
            current_distance = distance
            closest = candidate
    return closest


def _random_arround_(center):
    x, y = int(center[0] / TILE_SIZE), int(center[1] / TILE_SIZE)
    # FIXME: in the worst case this can be an infinite loop!!
    while True:
        x_offset = random.randint(-1, 1)
        y_offset = random.randint(-1, 1)
        if x_offset == y_offset == 0:
            continue
        return ((x + x_offset) * TILE_SIZE, (y + y_offset) * TILE_SIZE)


class TrackedGameObject:
    '''Every game object in the Room() but only data info'''
    def __init__(self, identifier, attributes=None):
        self.attribute = {
            IDENTIFIER: identifier,
            X: 0, Y: 0,
            STATE: 'initial'
        }
        if attributes:
            self.attribute.update(attributes)

    @property
    def x(self):
        '''Shortcut to horizontal position'''
        return self.attribute[X]

    @property
    def y(self):
        '''Shortcut to vertical position'''
        return self.attribute[Y]

    @property
    def identifier(self):
        '''Shortcut to identifier'''
        return self.attribute[IDENTIFIER]

    @property
    def position(self):
        '''Shortcut to object position attribute'''
        return (self.attribute[X], self.attribute[Y])

    @position.setter
    def position(self, new_position):
        '''Shortcut to set object position'''
        self.attribute[X] = new_position[0]
        self.attribute[Y] = new_position[1]
    
    @property
    def object_class(self):
        '''Shortcut to object class'''
        return self.attribute[OBJECT_CLASS]

    @property
    def object_type(self):
        '''Shortcut to object type'''
        return self.attribute[OBJECT_TYPE]

    @property
    def state(self):
        '''Shortcut to state'''
        return self.attribute[STATE]

    @state.setter
    def state(self, new_state):
        '''Shortcut to state'''
        self.attribute[STATE] = new_state


class RoomOrchestration:
    '''A running game instance'''
    def __init__(self, area):
        self._identifier_ = None
        self._area_ = area
        self._game_objects_ = {}
        self._level_ = None
        self._last_time_ = int(time.time())

    @property
    def identifier(self):
        '''Game instance identifier'''
        return self._identifier_

    @identifier.setter
    def identifier(self, new_identifier):
        '''Change instance identifier'''
        self._identifier_ = new_identifier

    @property
    def level(self):
        '''Get associated level'''
        return self._level_
    
    @level.setter
    def level(self, new_level):
        '''Set associated level'''
        self._level_ = new_level
        self._area_.event_handler = self.event_handler

    def start(self):
        '''Start new map'''
        self._game_objects_ = {}
        self._load_map_()
        for identifier, object_type, position in self._area_.getObjects():
            self._spawn_object_(identifier, object_type, *position)
        
        for identifier, attributes in self._area_.getActors():
            self._spawn_actor_(identifier, attributes)

        self._spawn_actor_(self.level.player.identifier, self.level.player.attribute)

    def _load_map_(self):
        map_name, map_autor, map_data = self._area_.getMap()
        self.fire_event(('load_room', map_name, map_data, map_autor), only_local=True)

    def _spawn_actor_(self, identifier, attributes):
        self.fire_event(('spawn_actor', identifier, attributes))

    def _spawn_object_(self, identifier, object_type, x, y):
        self.fire_event(('spawn_object', identifier, object_type, x, y))

    def _spawn_decoration_(self, decoration_type, x, y):
        self.fire_event(('spawn_decoration', decoration_type, x, y))

    def _kill_object_(self, identifier):
        self.fire_event(('kill_object', identifier))

    def _open_door_(self, player, door):
        self.fire_event(('open_door', player, door))

    def _set_attribute_(self, identifier, attribute, value):
        self.fire_event(('set_attribute', identifier, attribute, value))

    def _increase_attribute_(self, identifier, attribute, count):
        self.fire_event(('increase_attribute', identifier, attribute, count))

    def _warp_to_(self, identifier, position):
        self.fire_event(('warp_to', identifier, position))

    def _object_state_(self, identifier, state):
        self.fire_event(('set_state', identifier, state))

    def _get_objects_(self, type_id, exclude=None):
        found = []
        if exclude:
            if isinstance(exclude, TrackedGameObject):
                exclude = exclude.identifier
        for game_object in self._game_objects_.values():
            if game_object.identifier == exclude:
                continue
            if game_object.object_type == type_id:
                found.append(game_object)
        return found

    def event_handler(self, event):
        '''Handle event from the Room()'''
        event_type = event[0]
        event_parameters = event[1:]
        if event_type == 'collision':
            self._process_collision_(*event_parameters)
        elif event_type == 'spawn_actor':
            self.level.event_handler(event)
            identifier, attributes = event_parameters
            self._game_objects_[identifier] = TrackedGameObject(identifier, attributes)
        elif event_type == 'kill_object':
            self.level.event_handler(event)
            try:
                del self._game_objects_[event_parameters[0]]
            except KeyError:
                pass
        elif event_type == 'spawn_object':
            self.level.event_handler(event)
            identifier, object_type, x, y = event_parameters
            self._game_objects_[identifier] = TrackedGameObject(identifier, {
                X: x * TILE_SIZE,
                Y: y * TILE_SIZE,
                OBJECT_CLASS: 'door' if object_type in DOORS else 'item',
                OBJECT_TYPE: object_type
            })
        elif event_type == 'set_attribute':
            self.level.event_handler(event)
            identifier, attribute, value = event_parameters
            self._game_objects_[identifier].attribute[attribute] = value
        elif event_type == 'increase_attribute':
            self.level.event_handler(event)
            identifier, attribute, count = event_parameters
            current_value = self._game_objects_[identifier].attribute.get(attribute, 0)
            self._game_objects_[identifier].attribute[attribute] = current_value + count
        elif event_type == 'warp_to':
            self.level.event_handler(event)
            identifier, position = event_parameters
            self._game_objects_[identifier].position = position
        elif event_type == 'set_state':
            self.level.event_handler(event)
            identifier, state = event_parameters
            self._game_objects_[identifier].state = state

        else:
            self.level.event_handler(event)

    def fire_event(self, event, only_local=False):
        '''Fire event to the Room()'''
        if only_local:
            self.event_handler(event)
        else:
            self._area_.fire_event(event, only_local=False)

    def _process_collision_(self, object1, object2):
        if (object1 not in self._game_objects_) or (object2 not in self._game_objects_):
            return
        object1 = self._game_objects_[object1]
        object2 = self._game_objects_[object2]
        if object1.object_class == 'hero':
            if object2.object_class == 'item':
                # Player get an item
                if object2.object_type == game.objects.KEY:
                    self._kill_object_(object2.identifier)
                    self._increase_attribute_(object1.identifier, KEYS, 1)
                    self._increase_attribute_(object1.identifier, SCORE, POINTS_PER_KEY)
                elif object2.object_type == game.objects.TREASURE:
                    self._kill_object_(object2.identifier)
                    self._spawn_decoration_('smoke', *object2.position)
                    self._increase_attribute_(
                        object1.identifier, SCORE, random.randint(1, 4) * 1000
                    )
                elif object2.object_type == game.objects.JAR:
                    self._kill_object_(object2.identifier)
                    self._spawn_decoration_('smoke', *object2.position)
                    self._increase_attribute_(object1.identifier, LIFE, 100)
                elif object2.object_type == game.objects.HAM:
                    self._kill_object_(object2.identifier)
                    self._spawn_decoration_('smoke', *object2.position)
                    self._increase_attribute_(object1.identifier, LIFE, 50)
                elif object2.object_type == game.objects.TELEPORT:
                    destination = _closest_(
                        object1, self._get_objects_(game.objects.TELEPORT, exclude=object2)
                    )
                    if destination:
                        destination = _random_arround_(destination.position)
                        self._spawn_decoration_('smoke', *object1.position)
                        self._warp_to_(object1.identifier, destination)
                        self._spawn_decoration_('explosion', *destination)
                elif (object2.object_type == game.objects.EXIT) and (object1.state != 'exit'):
                    self._warp_to_(object1.identifier, object2.position)
                    self._object_state_(object1.identifier, 'exit')
                    self._increase_attribute_(object1.identifier, SCORE, POINTS_PER_LEVEL)
            elif object2.object_class == 'door':
                # Player try to open a door
                if object1.attribute.get(KEYS, 0) > 0:
                    self._increase_attribute_(object1.identifier, SCORE, POINTS_PER_DOOR)
                    self._open_door_(object1.identifier, object2.identifier)

    def update(self):
        '''Game loop iteration'''
        if int(time.time()) != self._last_time_:
            self._increase_attribute_(self.identifier, LIFE, -1)
            self._last_time_ = int(time.time())
