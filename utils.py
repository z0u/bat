#
# Copyright 2009-2011 Alex Fraser <alex@phatcore.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys

from functools import wraps

from bge import logic
import weakref

def replaceObject(name, original, time = 0):
	'''Like bge.types.scene.addObject, but:
	 - Transfers the properies of the original to the new object, and
	 - Deletes the original after the new one is created.'''
	scene = logic.getCurrentScene()
	newObj = scene.addObject(name, original, time)
	for prop in original.getPropertyNames():
		newObj[prop] = original[prop]
	original.endObject()
	return newObj

def owner(f):
	'''Decorator. Passes a single argument to a function: the owner of the
	current controller.'''
	@wraps(f)
	def f_new(owner=None):
		if owner == None:
			owner = logic.getCurrentController().owner
		elif owner.__class__.__name__ == 'SCA_PythonController':
			owner = owner.owner
		return f(owner)
	return f_new

def owner_cls(f):
	@wraps(f)
	def f_new(self, owner=None):
		if owner == None:
			owner = logic.getCurrentController().owner
		elif owner.__class__.__name__ == 'SCA_PythonController':
			owner = owner.owner
		return f(self, owner)
	return f_new

def controller(f):
	'''Decorator. Passes a single argument to a function: the current
	controller.'''
	@wraps(f)
	def f_new(c=None):
		if c == None:
			c = logic.getCurrentController()
		return f(c)
	return f_new

def controller_cls(f):
	'''Decorator. Passes a single argument to a function: the current
	controller.'''
	@wraps(f)
	def f_new(self, c=None):
		if c == None:
			c = logic.getCurrentController()
		return f(self, c)
	return f_new

@controller
def allSensorsPositive(c):
	'''Test whether all sensors are positive.
	
	Parameters:
	c: A controller.
	
	Returns: True if all sensors are positive.'''
	for s in c.sensors:
		if not s.positive:
			return False
	return True

@controller
def someSensorPositive(c):
	'''Test whether at least one sensor is positive.
	
	Parameters:
	c: A controller.
	
	Returns: True if at least one sensor is positive.'''
	for s in c.sensors:
		if s.positive:
			return True
	return False

def all_sensors_positive(f):
	'''Decorator. Only calls the function if all sensors are positive.'''
	@wraps(f)
	def f_new(*args, **kwargs):
		if not allSensorsPositive():
			return
		return f(*args, **kwargs)
	return f_new

def some_sensors_positive(f):
	'''Decorator. Only calls the function if one ore more sensors are
	positive.'''
	@wraps(f)
	def f_new(*args, **kwargs):
		if not someSensorPositive():
			return
		return f(*args, **kwargs)
	return f_new

def get_cursor():
	'''Gets the 'Cursor' object in the current scene. This object can be used
	when you need to call a method on a KX_GameObject, but you don't care which
	object it gets called on.

	See also bxt.types.get_wrapped_cursor.
	'''

	return logic.getCurrentScene().objects['Cursor']

def add_object(name, time = 0):
	'''Like KX_Scene.addObject, but doesn't need an existing object to position
	it. This uses the scene's cursor object (see get_cursor).
	'''

	scene = logic.getCurrentScene()
	return scene.addObject(name, get_cursor(), time)

def set_default_prop(ob, propName, value):
	'''Ensure a game object has the given property.

	Parameters:
	ob:       A KX_GameObject.
	propName: The property to check.
	value:    The value to assign to the property if it dosen't exist yet.
	'''
	if propName not in ob:
		ob[propName] = value

def add_state(ob, state):
	'''Add a set of states to the object's state.'''
	stateBitmask = 1 << (state - 1)
	ob.state |= stateBitmask

def rem_state(ob, state):
	'''Remove a state from the object's state.'''
	stateBitmask = 1 << (state - 1)
	ob.state &= (~stateBitmask)

def set_state(ob, state):
	'''Set the object's state. All current states will be un-set and replaced
	with the one specified.'''
	stateBitmask = 1 << (state - 1)
	ob.state = stateBitmask

def has_state(ob, state):
	'''Test whether the object is in the specified state.'''
	stateBitmask = 1 << (state - 1)
	return (ob.state & stateBitmask) != 0

class Counter:
	'''Counts the frequency of objects. This should only be used temporarily and
	then thrown away, as it keeps hard references to objects.
	'''

	def __init__(self):
		self.map = {}
		self.mode = None
		self.max = 0
		self.n = 0

	def add(self, ob):
		'''Add an object to this counter. If this object is the most frequent
		so far, it will be stored in the member variable 'mode'.'''
		count = 1
		if ob in self.map:
			count = self.map[ob] + 1
		self.map[ob] = count
		if count > self.max:
			self.max = count
			self.mode = ob
		self.n = self.n + 1

class FuzzySwitch:
	'''A boolean that only switches state after a number of consistent impulses.
	'''

	def __init__(self, delayOn, delayOff, startOn):
		self.delayOn = delayOn
		self.delayOff = 0 - delayOff
		self.on = startOn
		if startOn:
			self.current = self.delayOn
		else:
			self.current = self.delayOff

	def turn_on(self):
		self.current = max(0, self.current)
		if self.on:
			return

		self.current += 1
		if self.current == self.delayOn:
			self.on = True

	def turn_off(self):
		self.current = min(0, self.current)
		if not self.on:
			return

		self.current -= 1
		if self.current == self.delayOff:
			self.on = False

	def is_on(self):
		return self.on

class singleton:
	def __init__(self, *externs, prefix=None):
		self.externs = externs
		self.converted = False
		self.prefix = prefix
		self.instance = None

	def __call__(self, cls):
		if not self.converted:
			self.create_interface(cls)
			self.converted = True

		self.instance = cls()
		def get():
			return self.instance
		return get

	def create_interface(self, cls):
		'''Expose the nominated methods as top-level functions in the containing
		module.'''
		prefix = self.prefix
		if prefix == None:
			prefix = cls.__name__ + '_'

		module = sys.modules[cls.__module__]

		for methodName in self.externs:
			f = cls.__dict__[methodName]
			self.expose_method(methodName, f, module, prefix)

	def expose_method(self, methodName, method, module, prefix):
		def method_wrapper(*args, **kwargs):
			return method(self.instance, *args, **kwargs)

		method_wrapper.__name__ = '%s%s' % (prefix, methodName)
		method_wrapper.__doc__ = method.__doc__
		setattr(module, method_wrapper.__name__, method_wrapper)

class WeakPriorityQueue:
	'''A poor man's associative priority queue. This is likely to be slow. It is
	only meant to contain a small number of items.
	'''

	def __init__(self):
		'''Create a new, empty priority queue.'''

		self.queue = []
		self.priorities = {}

	def __len__(self):
		return len(self.queue)

	def __getitem__(self, y):
		'''Get the yth item from the queue. 0 is the bottom (oldest/lowest
		priority); -1 is the top (youngest/highest priority).
		'''

		return self.queue[y]()

	def __contains__(self, item):
		ref = weakref.ref(item)
		return ref in self.priorities

	def _index(self, ref, *args, **kwargs):
		return self.queue.index(ref, *args, **kwargs)

	def index(self, item, *args, **kwargs):
		return self._index(weakref.ref(item), *args, **kwargs)

	def push(self, item, priority):
		'''Add an item to the end of the queue. If the item is already in the
		queue, it is removed and added again using the new priority.

		Parameters:
		item:     The item to store in the queue.
		priority: Items with higher priority will be stored higher on the queue.
		          0 <= priority. (Integer)
		'''

		def autoremove(r):
			self._discard(r)

		ref = weakref.ref(item, autoremove)

		if ref in self.priorities:
			self.discard(item)

		i = len(self.queue)
		while i > 0:
			refOther = self.queue[i - 1]
			priOther = self.priorities[refOther]
			if priOther <= priority:
				break
			i -= 1
		self.queue.insert(i, ref)

		self.priorities[ref] = priority

		return i

	def _discard(self, ref):
		self.queue.remove(ref)
		del self.priorities[ref]

	def discard(self, item):
		'''Remove an item from the queue.

		Parameters:
		key: The key that was used to insert the item.
		'''
		self._discard(weakref.ref(item))

	def pop(self):
		'''Remove the highest item in the queue.

		Returns: the item that is being removed.

		Raises:
		IndexError: if the queue is empty.
		'''

		ref = self.queue.pop()
		del self.priorities[ref]
		return ref()

	def top(self):
		return self[-1]

@singleton()
class EventBus:
	'''Delivers messages to listeners.'''

	def __init__(self):
		self.listeners = weakref.WeakSet()
		self.eventCache = {}

	def addListener(self, listener):
		self.listeners.add(listener)

	def remListener(self, listener):
		self.listeners.remove(listener)

	def notify(self, event):
		'''Send a message.'''

		for listener in self.listeners:
			listener.onEvent(event)
		self.eventCache[event.message] = event

	def replayLast(self, target, message):
		'''Re-send a message. This should be used by new listeners that missed
		out on the last message, so they know what state the system is in.'''

		if message in self.eventCache:
			event = self.eventCache[message]
			target.onEvent(event)

class EventListener:
	'''Interface for an object that can receive messages.'''
	def onEvent(self, event):
		pass

class Event:
	def __init__(self, message, body=None):
		self.message = message
		self.body = body

	def __str__(self):
		return "Event(%s, %s)" % (str(self.message), str(self.body))

class WeakEvent(Event):
	'''An event whose body my be destroyed before it is read. Use this when
	the body is a game object (which will need to be wrapped in
	bxt.types.ProxyGameObject).'''
	def __init__(self, message, body):
		def autoremove(target):
			self._body = None

		self.message = message
		if body == None:
			self._body = None
		else:
			self._body = weakref.ref(body, autoremove)

	def _get_body(self):
		if self._body == None:
			return None
		else:
			return self._body()
	body = property(_get_body)
