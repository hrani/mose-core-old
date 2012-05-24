# trbcell.py --- 
# 
# Filename: trbcell.py
# Description: 
# Author: Subhasis Ray
# Maintainer: 
# Created: Fri Mar  9 23:17:17 2012 (+0530)
# Version: 
# Last-Updated: Thu May 24 16:53:01 2012 (+0530)
#           By: subha
#     Update #: 379
# URL: 
# Keywords: 
# Compatibility: 
# 
# 

# Commentary: 
# 
# 
# 
# 

# Change log:
# 
# 2012-03-09 23:17:24 (+0530) Subha started porting the cell.py file
# from old moose to dh_branch.
# 

# Code:

from collections import defaultdict
import moose
import config
from config import logger
import nachans
import kchans
import ar
import cachans
import capool
from init import init_chanlib
        
def read_keyvals(filename):
    """Read the mapping between key value pairs from file.
    
    The file filename should have two columns:

    key value

    """
    ret = defaultdict(set)
    with(open(filename, 'r')) as level_file:
        for line in level_file:
            tokens = line.split()
            if not tokens:
                continue
            if len(tokens) != 2:
                print filename, ' - Tokens: ', tokens, len(tokens)
                return None
            ret[int(tokens[1])].add(int(tokens[0]))
    return ret

def adjust_chanlib(cdict):
    """Update the revarsal potentials for channels. Set the initial X
    value for AR channel. Set the tau for Ca pool."""
    for ch in init_chanlib().values():
        if isinstance(ch, kchans.KChannel):
            ch.Ek = cdict['EK']
        elif isinstance(ch, nachans.NaChannel):
            ch.Ek = cdict['ENa']
        elif isinstance(ch, cachans.CaChannel):
            ch.Ek = cdict['ECa']
        elif isinstance(ch, ar.AR):
            ch.Ek = cdict['EAR']
            ch.X = cdict['X_AR']        
        elif isinstance(ch, capool.CaPool):
            ch.tau = cdict['TauCa']            

def read_prototype(cls, cdict):
    """Read the cell prototype file for the specified class. The
    channel properties are updated using values in cdict."""
    celltype = cls.__name__
    filename = '%s/%s.p' % (config.modelSettings.protodir, celltype)
    logger.debug('Reading prototype file %s' % (filename))
    adjust_chanlib(cdict)
    cellpath = '%s/%s' % (config.modelSettings.libpath, celltype)
    if moose.exists(cellpath):
        return moose.element(cellpath)
    for handler in logger.handlers:
        handler.flush()
    proto = moose.loadModel(filename, cellpath)
    # If prototype files do not have absolute compartment positions,
    # set the compartment postions to origin. This will avoid
    # incorrect assignemnt of position when the x/y/z values in
    # prototype file is just to for setting the compartment length.
    if not config.has_comp_pos:
        for comp in moose.wildCardFind('%s/##[TYPE=Compartment]' % (proto.path)):
            comp.x = 0.0
            comp.y = 0.0
            comp.z = 0.0
    leveldict = read_keyvals('%s/%s.levels' % (config.protodir, celltype))
    depths = read_keyvals('%s/%s.depths' % (config.protodir, celltype))
    depthdict = {}
    for level, depthset in depths.items():
        if len(depthset) != 1:
            raise Exception('Depth set must have only one entry.')
        depthdict[level] = depthset.pop()
    assign_depths(proto, depthdict, leveldict)
    return proto

def assign_depths(cell, depthdict, leveldict):
    """Assign depths to the compartments in the cell. The original
    model assigns sets of compartments to particular levels and a
    depth is specified for each level. This should not be required if
    we have the z value in prototype file.

    cell : (prototype) cell instance

    depth : dict mapping level no. to physical depth

    level : dict mapping level no. to compartment nos. belonging to
    that level.
    """
    if not depthdict:
        return
    for level, complist in leveldict.items():
        z = depthdict[level]
        for comp_number in complist:
            comp = moose.element('%s/comp_%d' % (cell.path, comp_number))
            comp.z = z

            
class CellMeta(type):
    def __new__(cls, name, bases, cdict):        
        proto = read_prototype(cls, cdict)
        if 'soma_tauCa' in cdict:
            moose.element(proto.path + '/comp_1/CaPool').tau = cdict['soma_tauCa']
        cdict['prototype'] = proto
        return type.__new__(cls, name, bases, cdict)

    
class CellBase(moose.Cell):
    __metaclass__ = CellMeta
    def __init__(self, *args):
        moose.Cell.__init__(self, *args)
        
    def comp(self, number):
        return moose.element('%s/comp_%d' % (self.path, number))

    @property
    def get_soma(self):
        return self.comp(1)

    @property
    def get_presynaptic(self):
        """Presynaptic compartment. Each subclass should define
        _presynaptic as the index of this compartment."""
        return self.comp[self.__class__._presynaptic]


class SupPyrRS(CellBase):
    _presynaptic = 72
    ENa = 50e-3
    EK = -95e-3
    ECa = 125e-3
    EAR = -35e-3
    EGABA = -81e-3
    TauCa = 20e-3
    soma_tauCa  = 100e-3

    
class SupPyrFRB(CellBase):
    _presynaptic = 72
    ENa = 50e-3,
    EK = -95e-3,
    EAR = -35e-3,
    ECa = 125e-3,
    EGABA = -81e-3,
    TauCa = 20e-3    
    soma_tauCa = 100e-3

    
class SupLTS(CellBase):
    _presynaptic = 59
    ENa = 50e-3
    EK = -100e-3
    ECa = 125e-3
    EAR = -40e-3 # dummy to set things back to original
    EGABA = -75e-3 # Sanchez-Vives et al. 1997 
    TauCa = 20e-3
    X_AR = 0.25
    soma_tauCa = 50e-3
    

class SupAxoaxonic(CellBase):
    _presynaptic = 59
    ENa = 50e-3
    EK = -100e-3
    ECa = 125e-3
    EAR = -40e-3
    EGABA = -75e-3
    X_AR = 0.0
    TauCa = 20e-3
    soma_tauCa = 50e-3


class SupBasket(CellBase):
    _presynaptic = 59
    ENa = 50e-3
    EK = -100e-3
    EAR = -40e-3
    ECa = 125e-3
    EGABA = -75e-3 # Sanchez-Vives et al. 1997 
    TauCa = 20e-3
    X_AR = 0.0
    soma_tauCa = 50e-3

    
class SpinyStellate(CellBase):
    """Spiny-stellate cells of layer 4."""
    _presynaptic = 57
    ENa = 50e-3
    EK = -100e-3
    EAR = -40e-3
    ECa = 125e-3
    EGABA = -75e-3
    TauCa = 20e-3
    X_AR = 0.0
    soma_tauCa = 50e-3

    
class NontuftedRS(CellBase):
    _presynaptic = 48
    ENa = 50e-3
    EK = -95e-3
    EAR = -35e-3
    ECa = 125e-3
    EGABA = -75e-3 # Sanchez-Vives et al. 1997 
    TauCa = 20e-3
    X_AR = 0.25
    soma_tauCa = 100e-3


class TuftedIB(CellBase):    
    _presynaptic = 60
    ENa = 50e-3
    EK = -95e-3
    EAR = -35e-3
    ECa = 125e-3
    EGABA = -75e-3 # Sanchez-Vives et al. 1997 
    TauCa = 1e-3/0.075
    X_AR = 0.25
    soma_tauCa = 100e-3
    
    # for compartments in level 2, i.e. comp_2, 5, 6 have tauCa = 1e-3/0.02        
    @classmethod
    def post_init(cls):
        moose.element(cls.prototype.path + '/comp_2/CaPool').tau = 1e-3/0.02
        moose.element(cls.prototype.path + '/comp_5/CaPool').tau = 1e-3/0.02
        moose.element(cls.prototype.path + '/comp_6/CaPool').tau = 1e-3/0.02


TuftedIB.post_init()


class TuftedRS(CellBase):
    _presynaptic = 60
    ENa = 50e-3
    EK = -95e-3
    EAR = -35e-3
    ECa = 125e-3
    EGABA = -75e-3 # Sanchez-Vives et al. 1997 
    TauCa = 1e-3/0.075
    X_AR = 0.25
    soma_tauCa = 100e-3
    
    @classmethod
    def post_init(cls):
        moose.element(cls.prototype.path + '/comp_2/CaPool').tau = 1e-3/0.02
        moose.element(cls.prototype.path + '/comp_5/CaPool').tau = 1e-3/0.02
        moose.element(cls.prototype.path + '/comp_6/CaPool').tau = 1e-3/0.02

TuftedRS.post_init()


class DeepLTS(CellBase):
    _presynaptic = 59
    ENa = 50e-3,
    EK = -100e-3,
    EAR = -40e-3,
    ECa = 125e-3,
    EGABA = -75e-3, # Sanchez-Vives et al. 1997 
    TauCa = 20e-3,
    X_AR = 0.25
    soma_tauCa = 50e-3


class DeepAxoaxonic(CellBase):
    _presynaptic = 59
    ENa = 50e-3
    EK = -100e-3
    ECa = 125e-3
    EAR = -40e-3
    EGABA = -75e-3
    X_AR = 0.0
    TauCa = 20e-3
    soma_tauCa = 50e-3

    
class DeepBasket(CellBase):
    _presynaptic = 59
    ENa = 50e-3
    EK = -100e-3
    EAR = -40e-3
    ECa = 125e-3
    EGABA = -75e-3 # Sanchez-Vives et al. 1997 
    TauCa = 20e-3
    X_AR = 0.25
    soma_tauCa = 50e-3

    
class TCR(CellBase):
    _presynaptic = 135
    ENa = 50e-3
    EK = -95e-3
    EAR = -35e-3
    ECa = 125e-3
    EGABA = -81e-3
    TauCa = 20e-3
    X_AR = 0.25
    soma_tauCa = 50e-3


class nRT(CellBase):
    _presynaptic = 59
    ENa = 50e-3
    EK = -100e-3
    EAR = -40e-3
    ECa = 125e-3
    EGABA = -75e-3 # Sanchez-Vives et al. 1997 
    TauCa = 20e-3
    X_AR = 0.0
    soma_tauCa = 50e-3


_cellprototypes = {}

def initPrototypes():
    global _cellprototypes
    if _cellprototypes:
        return _cellprototypes
    _cellprototypes = {
        'SupPyrRS': SupPyrRS(SupPyrRS.prototype),
        'SupPyrFRB': SupPyrFRB(SupPyrFRB.prototype),
        'SupLTS': SupLTS(SupLTS.prototype),
        'SupAxoaxonic': SupAxoaxonic(SupAxoaxonic.prototype),
        'SupBasket': SupBasket(SupBasket.prototype),
        'SpinyStellate': SpinyStellate(SpinyStellate.prototype),
        'NontuftedRS': NontuftedRS(NontuftedRS.prototype),
        'TuftedIB': TuftedIB(TuftedIB.prototype),
        'TuftedRS': TuftedRS(TuftedRS.prototype),
        'DeepLTS':  DeepLTS(DeepLTS.prototype),
        'DeepAxoaxonic': DeepAxoaxonic(DeepAxoaxonic.prototype),
        'DeepBasket': DeepBasket(DeepBasket.prototype),
        'TCR': TCR(TCR.prototype),
        'nRT': nRT(nRT.prototype),
    }
    return _cellprototypes
    
# 
# trbcell.py ends here