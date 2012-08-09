#
# Copyright 2009-2012 Alex Fraser <alex@phatcore.com>
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

from collections import namedtuple

import aud
import mathutils
import bge

import bxt

MIN_VOLUME = 0.001

#
# A mapping from sound name to actuator index. This lets play_with_random_pitch
# cycle through different samples for a named sound.
#
_SoundActuatorIndices = {}
_volume_map = {}

def set_volume(object_name, volume):
	'''
	Sets the volume for a particular object. If that object later calls one the
	methods in this module to play a sound, the volume specified here will be
	used.
	'''
	_volume_map[object_name] = volume

@bxt.utils.all_sensors_positive
@bxt.utils.controller
def play_with_random_pitch(c):
	'''
	Play a sound with a random pitch. The pitch range is defined by the
	controller's owner using the properties PitchMin and PitchMax.

	Sensors:
	<one>:  If positive and triggered, a sound will be played.

	Actuators:
	<one+>: Each will be played in turn.

	Controller properties:
	PitchMin: The minimum pitch (float).
	PitchMax: The maximum pitch (float).
	SoundID:  The name of the sound (any type). This lets different objects with
	          the same SoundID coordinate the sequence that the sounds are
	          played in. Note that if controllers with the same SoundID have
	          different numbers of actuators, the additional actuators are not
	          guaranteed to play.
	'''
	o = c.owner

	try:
		o['PitchMin']
	except KeyError:
		o['PitchMin'] = 0.8
	try:
		o['PitchMax']
	except KeyError:
		o['PitchMax'] = 1.2

	#
	# Select an actuator.
	#
	i = 0
	try:
		i = _SoundActuatorIndices[o.name]
	except KeyError:
		_SoundActuatorIndices[o.name] = 0
		i = 0

	i = i % len(c.actuators)
	a = c.actuators[i]
	_SoundActuatorIndices[o.name] = i + 1

	#
	# Set the pitch and activate!
	#
	a.pitch = bxt.bmath.lerp(o['PitchMin'], o['PitchMax'], bge.logic.getRandomFloat())
	try:
		a.volume = _volume_map[o.name]
	except KeyError:
		pass
	c.activate(a)

@bxt.utils.controller
def fade(c):
	'''
	Causes a sound to play a long as its inputs are active. On activation, the
	sound fades in; on deactivation, it fades out. The fade rate is determined
	by the owner's SoundFadeFac property (0.0 <= SoundFadeFac <= 1.0).

	Sensors:
	sAlways:  Fires every frame to provide the fading effect.
	<one+>:   If any are positive, the sound will turn on. Otherwise the sound
	          will turn off.

	Actuators:
	<one>:    A sound actuator.

	Controller properties:
	VolumeMult:    The maximum volume (float).
	SoundFadeFac:  The response factor for the volume (float).
	'''
	_fade(c, 1.0)

def _fade(c, maxVolume):
	a = c.actuators[0]
	o = a.owner

	# Wait a few frames before allowing sound to be played. This is a filthy
	# hack to prevent objects from being noisy when they spawn - i.e. when they
	# tend to have a bit of initial velocity.
	try:
		if o['SoundWait'] > 0:
			o['SoundWait'] -= 1
			return
	except:
		o['SoundWait'] = 20
		return

	try:
		o['SoundFadeFac']
	except KeyError:
		o['SoundFadeFac'] = 0.05

	if o.name in _volume_map:
		maxVolume *= _volume_map[o.name]

	targetVolume = 0.0
	for s in c.sensors:
		if s.name == "sAlways":
			continue
		if s.positive:
			targetVolume = maxVolume
			break

	a.volume = bxt.bmath.lerp(a.volume, targetVolume, o['SoundFadeFac'])
	if a.volume > MIN_VOLUME:
		c.activate(a)
	else:
		c.deactivate(a)

def _modulate(speed, c):
	o = c.owner

	try:
		o['SoundModScale']
	except KeyError:
		o['SoundModScale'] = 0.01
	try:
		o['PitchMin']
	except KeyError:
		o['PitchMin'] = 0.8
	try:
		o['PitchMax']
	except KeyError:
		o['PitchMax'] = 1.2

	factor = 0.0
	if speed > 0.0:
		factor = bxt.bmath.approach_one(speed, o['SoundModScale'])

	a = c.actuators[0]
	a.pitch = bxt.bmath.lerp(o['PitchMin'], o['PitchMax'], factor)

	_fade(c, factor)

@bxt.utils.controller
def modulate_by_linv(c):
	'''
	Change the pitch and volume of the sound depending on the angular velocity
	of the controller's owner.

	Sensors:
	sAlways:  Fires every frame to provide the fading effect.
	<others>: At least one other. If any are positive, the sound will turn on.
	          Otherwise the sound will turn off.

	Actuators:
	<one>:    A sound actuator.

	Controller properties:
	SoundModScale: The rate at which the pitch increases (float).
	PitchMin:      The minimum pitch (when speed = 0) (float).
	PitchMax:      The maximum pitch (as speed approaches infinity) (float).
	VolumeMult:    The maximum volume (as speed approaches infinity) (float).
	SoundFadeFac:  The response factor for the volume (float).
	'''
	o = c.owner
	linV = mathutils.Vector(o.getLinearVelocity(False))
	_modulate(linV.magnitude, c)

@bxt.utils.controller
def modulate_by_angv(c):
	'''
	Change the pitch and volume of the sound depending on the angular velocity
	of the controller's owner.

	Sensors:
	sAlways:  Fires every frame to provide the fading effect.
	<others>: At least one other. If any are positive, the sound will turn on.
	          Otherwise the sound will turn off.

	Actuators:
	<one>:    A sound actuator.

	Controller properties:
	SoundModScale: The rate at which the pitch increases (float).
	PitchMin:      The minimum pitch (when speed = 0) (float).
	PitchMax:      The maximum pitch (as speed approaches infinity) (float).
	VolumeMult:    The maximum volume (as speed approaches infinity) (float).
	SoundFadeFac:  The response factor for the volume (float).
	'''
	o = c.owner
	angV = mathutils.Vector(o.getAngularVelocity(False))
	_modulate(angV.magnitude, c)

# Warnings! Kept in a set so they're only printed once.
_warnings_printed = set()

# These are sounds that have a location. We manage their location manually to
# work around this bug:
# http://projects.blender.org/tracker/?func=detail&atid=306&aid=32096&group_id=9
_handles= []
HandleBXT = namedtuple('HandleBXT', ['ident', 'handle', 'source'])
_localisable_handles = []
Handle3D = namedtuple('Handle3D', ['ob', 'handle', 'source'])

def play_sample(filename, volume=1.0, pitchmin=1.0, pitchmax=1.0,
			ob=None, distmin=10.0, distmax=1000000.0, loop=False):
	'''Play a sound file.'''

	# Don't play sound if it's already playing.
	# TODO: Make this better: it should:
	#  - Only play sound if it woulnd't bump off a higher-priority sound.
	#  - Be able to play multiple copies of a sound if they are tied to
	#    different objects or something.
	for h in _handles:
		if h.ident == filename:
			return

	try:
		dev = aud.device()
		path = bge.logic.expandPath(filename)
		sample = aud.Factory(path)

		if volume != 1.0:
			sample = sample.volume(volume)

		if pitchmax != 1.0 or pitchmin != 1.0:
			pitch = bxt.bmath.lerp(pitchmin, pitchmax,
					bge.logic.getRandomFloat())
			sample = sample.pitch(pitch)

		if loop:
			sample = sample.loop(-1)

		#print("Playing %s at %s" % (filename, ob))
		handle = dev.play(sample)
		_handles.append(HandleBXT(filename, handle, filename))

		if ob is not None:
			handle.location = ob.worldPosition
			handle.relative = False
			handle.distance_reference = distmin
			handle.distance_maximum = distmax
			handle.attenuation = 10.0
			_localisable_handles.append(Handle3D(ob, handle, filename))

	except aud.error as e:
		if not filename in _warnings_printed:
			print("Error playing sound file %s" % filename)
			print(e)
		_warnings_printed.add(filename)

def play_random_sample(filenames, volume=1.0, pitchmin=1.0, pitchmax=1.0,
			ob=None, distmin=10.0, distmax=1000000.0):
	'''Play a random sound from a set of files.'''
	i = int(len(filenames) * bge.logic.getRandomFloat())
	play_sample(filenames[i], volume=volume, pitchmin=pitchmin,
			pitchmax=pitchmax, ob=ob, distmin=distmin, distmax=distmax)

def stop(identifier):
	# Don't need to copy list because iteration stops after removal.
	for h in _handles:
		if h.ident == identifier:
			h.handle.stop()
			_handles.remove(h)
			return

def update():
	'''
	Update the locations of 3D sounds to match their objects. Should be called
	once per logic tick.
	'''
	def _update():
		for h in list(_handles):
			if not h.handle.status:
				_handles.remove(h)
				continue
		for h3d in list(_localisable_handles):
			# Ignore sounds that have stopped.
			if h3d.ob.invalid or not h3d.handle.status:
				_localisable_handles.remove(h3d)
				continue

			h3d.handle.location = h3d.ob.worldPosition

	dev = aud.device()
	dev.lock()
	try:
		_update()
	finally:
		dev.unlock()
