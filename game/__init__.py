#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

'''
    Game base and states
'''


import copy
import uuid
import random

import game.pyxeltools
from game.common import LIFE, LEVEL_COUNT, AVAILABLE_OBJECT_IDS, EMPTY_TILE, NULL_TILE, HEROES,\
    OBJECT_CLASS, OBJECT_TYPE, IDENTIFIER
from game.pyxeltools import TILE_SIZE, load_json_map


class GameState:
    '''Game state base class'''
    def __init__(self, parent=None):
        self.parent = parent

    def wake_up(self):
        '''Executed when state begins'''
        pass

    def suspend(self):
        '''Executed when state ends'''
        pass

    def update(self):
        '''Game loop iteration'''
        pass

    def render(self):
        '''Draw single frame'''
        pass

    def go_to_state(self, new_state):
        '''Go to next state of the game'''
        self.parent.enter_state(new_state)


class PlayerData:
    '''Store player data accross the states of the game'''
    def __init__(self, hero_class, steer='Player1', initial_attributes=None, identifier=None):
        self.attribute = {
            OBJECT_CLASS: 'hero',
            OBJECT_TYPE: hero_class,
            'steer_id': steer,
            'identifier': identifier or str(uuid.uuid4()),
            LEVEL_COUNT: 1
        }
        if initial_attributes:
            self.attribute.update(initial_attributes)
    
    @property
    def identifier(self):
        return self.attribute[IDENTIFIER]

    @property
    def hero_class(self):
        return self.attribute[OBJECT_TYPE]

    @property
    def steer_id(self):
        return self.attribute['steer_id']


class DungeonMap:
    '''Store a list of rooms'''
    def __init__(self, levels):
        self._original_ = levels
        self.reset()

    def reset(self):
        self._levels_ = copy.copy(self._original_)
        self._levels_.reverse()
        self._current_area_ = None

    @property
    def next_area(self):
        if self._levels_:
            self._current_area_ = LocalArea(self._levels_.pop())
            return self._current_area_

    @property
    def finished(self):
        return not self._levels_

    def abandon_area(self):
        self._current_area_.abandon()


class LocalArea:
    def __init__(self, level):
        self.event_handler = self.__discard_event__
        self.roomName, self.author, roomData = load_json_map(level)
        self.objects = []
        self.roomData = []
        y = 0
        for row in roomData:
            x = 0
            filteredRow = []
            for tile in row:
                if (tile in AVAILABLE_OBJECT_IDS):
                    filteredRow.append(EMPTY_TILE)
                    self.objects.append((str(uuid.uuid4()), tile, (x, y)))
                elif (tile == NULL_TILE):
                    filteredRow.append(EMPTY_TILE)
                else:
                    filteredRow.append(tile)
                x += 1
            y += 1
            self.roomData.append(filteredRow)

    def getMap(self):
        return self.roomName, self.author, self.roomData

    def getObjects(self):
        return self.objects

    def getActors(self):
        return []
    
    def fire_event(self, event, only_local=False):
        if not only_local:
            self.event_handler(event)

    def abandon(self):
        pass

    def __discard_event__(self, event):
        pass


class Game:
    '''This class wraps the game loop created by pyxel'''
    def __init__(self, hero_class, dungeon, identifier=None):
        self._identifier_ = identifier or str(uuid.uuid4())
        self._states_ = {}
        self._current_state_ = None
        self._initial_state_ = None
        self._player_ = PlayerData(hero_class, identifier=self._identifier_)
        self._dungeon_ = dungeon

    @property
    def identifier(self):
        '''Game unique identifier'''
        return self._identifier_

    @property
    def player(self):
        '''Player data'''
        return self._player_

    @property
    def dungeon(self):
        '''Dungeon data'''
        return self._dungeon_

    def start(self):
        '''Start pyxel game loop'''
        game.pyxeltools.run(self)

    def reset(self):
        '''Reset game states'''
        self._dungeon_.reset()

    def add_state(self, game_state, identifier):
        '''Add new state to the game'''
        self._states_[identifier] = game_state
        if self._current_state_ is None:
            self.enter_state(identifier)
            self._initial_state_ = identifier

    def enter_state(self, new_state):
        '''Change game state'''
        if new_state not in self._states_:
            raise ValueError('Unknown state: "{}"'.format(new_state))
        if self._current_state_ is not None:
            self._current_state_.suspend()
        self._current_state_ = self._states_[new_state](self)
        self._current_state_.wake_up()

    def update(self):
        '''Game loop iteration'''
        self._current_state_.update()

    def render(self):
        '''Draw a single frame'''
        self._current_state_.render()
