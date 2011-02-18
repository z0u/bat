#
# Copyright 2009-2010 Alex Fraser <alex@phatcore.com>
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
'''
Created on 13/02/2010

@author: alex
'''

import bxt
import mathutils

DEBUG = False

@bxt.types.gameobject(prefix='FF_')
class ForceField(bxt.types.ProxyGameObject):
	def __init__(self, owner):
		bxt.types.ProxyGameObject.__init__(self, owner)
		self.set_state(2)
		if DEBUG:
			self.forceMarker = bxt.utils.add_object('VectorMarker', 0)
			self.forceMarker.color = bxt.render.YELLOW

	def modulate(self, distance, limit):
		'''
		To visualise this function, try it in gnuplot:
			f(d, l) = (d*d) / (l*l)
			plot [0:10][0:1] f(x, 10)
		'''
		return (distance * distance) / (limit * limit)

	def get_magnitude(self, distance):
		effect = 0.0
		if distance < self['FFDist1']:
			effect = self.modulate(distance, self['FFDist1'])
		else:
			effect = 1.0 - self.modulate(distance - self['FFDist1'],
										 self['FFDist2'])
		if effect > 1.0:
			effect = 1.0
		if effect < 0.0:
			effect = 0.0
		return self['FFMagnitude'] * effect

	@bxt.utils.controller_cls
	def touched(self, c):
		actors = set()
		for s in c.sensors:
			if not s.positive:
				continue
			for ob in s.hitObjectList:
				actors.add(ob)

		for a in actors:
			self.touchedSingle(a)

	def touchedSingle(self, actor, factor = 1.0):
		'''Called when an object is inside the force field.'''
		pos = mathutils.Vector(actor.worldPosition)

		if (bxt.math.manhattan_dist(pos, self.worldPosition) >
			self['FFDist2']):
			return

		pos = bxt.math.to_local(self, pos)
		if 'FFZCut' in self and self['FFZCut'] and (pos.z > 0.0):
			return

		vec = self.get_force_direction(pos)
		dist = vec.magnitude
		if dist != 0.0:
			vec.normalize()
		magnitude = self.get_magnitude(dist)
		vec *= magnitude * factor
		vec = bxt.math.to_world_vec(self, vec)

		if DEBUG:
			self.forceMarker.worldPosition = actor.worldPosition
			if vec.magnitude > bxt.math.EPSILON:
				self.forceMarker.alignAxisToVect(vec, 2)
				self.forceMarker.color = bxt.render.YELLOW
			else:
				self.forceMarker.color = bxt.render.BLACK

		linV = mathutils.Vector(actor.getLinearVelocity(False))
		linV += vec
		actor.setLinearVelocity(linV, False)

	def get_force_direction(self, localPos):
		'''Returns the Vector along which the acceleration will be applied, in
		local space.'''
		pass

@bxt.types.gameobject()
class Linear(ForceField):
	def __init__(self, owner):
		ForceField.__init__(self, owner)

	def get_force_direction(self, posLocal):
		return bxt.math.to_local_vec(self, self.getAxisVect(bxt.math.YAXIS))

	def modulate(self, distance, limit):
		'''
		To visualise this function, try it in gnuplot:
			f(d, l) = d / l
			plot [0:10][0:1] f(x, 10)
		'''
		return distance / limit

@bxt.types.gameobject()
class Repeller3D(ForceField):
	'''
	Repels objects away from the force field's origin.

	Object properties:
	FFMagnitude: The maximum acceleration.
	FFDist1: The distance from the origin at which the maximum acceleration will
		be applied.
	FFDist2: The distance from the origin at which the acceleration will be
		zero.
	FFZCut: If True, force will only be applied to objects underneath the force
		field's XY plane (in force field local space).
	'''
	def __init__(self, owner):
		ForceField.__init__(self, owner)

	def get_force_direction(self, posLocal):
		return posLocal

@bxt.types.gameobject()
class Repeller2D(ForceField):
	'''
	Repels objects away from the force field's origin on the local XY axis.

	Object properties:
	FFMagnitude: The maximum acceleration.
	FFDist1: The distance from the origin at which the maximum acceleration will
		be applied.
	FFDist2: The distance from the origin at which the acceleration will be
		zero.
	FFZCut: If True, force will only be applied to objects underneath the force
		field's XY plane (in force field local space).
	'''
	def __init__(self, owner):
		ForceField.__init__(self, owner)

	def get_force_direction(self, posLocal):
		vec = mathutils.Vector(posLocal)
		vec.z = 0.0
		return vec

@bxt.types.gameobject()
class Vortex2D(ForceField):
	'''
	Propels objects around the force field's origin, so that the rotate around
	the Z-axis. Rotation will be clockwise for positive magnitudes. Force is
	applied tangentially to a circle around the Z-axis, so the objects will tend
	to spiral out from the centre. The magnitude of the acceleration varies
	depending on the distance of the object from the origin: at the centre, the
	acceleration is zero. It ramps up slowly (r-squared) to the first distance
	marker; then ramps down (1 - r-squared) to the second.

	Object properties:
	FFMagnitude: The maximum acceleration.
	FFDist1: The distance from the origin at which the maximum acceleration will
		be applied.
	FFDist2: The distance from the origin at which the acceleration will be
		zero.
	FFZCut: If True, force will only be applied to objects underneath the force
		field's XY plane (in force field local space).
	'''

	def __init__(self, owner):
		ForceField.__init__(self, owner)

	def get_force_direction(self, posLocal):
		tan = mathutils.Vector((posLocal.y, 0.0 - posLocal.x, 0.0))
		return tan