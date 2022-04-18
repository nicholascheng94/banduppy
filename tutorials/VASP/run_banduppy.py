#!/usr/bin/env python3

### you need to install packages `banduppy` and `irrep` from pip

# if you whant calculations with SOC or without
spinorbit = False


#disable some of the options to avoid repeating
do_self_consistent = True
do_non_self_consistent = True
do_unfold = True
do_plot = True<

import banduppy

import shutil,os,glob
from subprocess import run
import numpy as np
import pickle

vasppath="/app/theorie/vasp/bin"

nproc=16
vasp=f"mpirun -np {nproc}  {vasppath}/vasp_ncl".split()


unfold_path=banduppy.UnfoldingPath(
            supercell= [[-1 ,  1 , 1],
                        [1  , -1 , 1],
                        [1  ,  1 ,-1]] ,   # How the SC latticevectors are expressed in the PC basis (should be a 3x3 array of integers)
            pathPBZ=[[1/2,1/2,1/2], [0,0,0],[1/2,0,1/2], [5/8,1/4,5/8], None, [3/8,3/8,3/4], [0,0,0]],  # Path nodes in reduced coordinates in the primitive BZ. if the segmant is skipped, put a None between nodes
            nk=(23,27,9,29),  #  number of k-points in each non-skipped segment. Or just give one number, if they are equal
             labels="LGXUKG" )   # or ['L','G','X','U','K','G']



unfold=banduppy.Unfolding(
            supercell= [[-1 ,  1 , 1],
                        [1  , -1 , 1],
                        [1  ,  1 ,-1]] , # How the SC latticevectors are expressed in the PC basis (should be a 3x3 array of integers)
            kpointsPBZ =  np.array([np.linspace(0.0,0.5,12)]*3).T # just a list of k-points (G-L line in this example)
                              )

kpointsPBZ=unfold_path.kpoints_SBZ_str()   # as tring  containing the k-points to beentered into the PWSCF input file  after 'K_POINTS crystal ' line. maybe transformed to formats of other codes  if needed

try:
    print ("unpickling unfold")
    unfold_path=pickle.load(open("unfold-path.pickle","rb"))
    unfold=pickle.load(open("unfold.pickle","rb"))
except Exception as err:
    print("error while unpickling unfold '{}',  unfolding it".format(err))
    try:
        print ("unpickling bandstructure")
        bands=pickle.load(open("bandstructure.pickle","rb"))  
        print ("unpickling - success")
    except Exception as err:
        print("Unable to unpickle  bandstructure '{}' \n  Reading bandstructurefrom .save folder ".format(err)) 
        try: 
            ####   This line reads the bandstructure written by QE into an pobject bandStructure of the irrep code.
            bands=banduppy.BandStructure(code="vasp", spinor="True",fPOS = "POSCAR",fWAV = "WAVECAR")
            ####  this is a shortcut to   bands=irrep.bandstructure.BandStructure(...)
            ####  For spin-polarised calculations you need to select spin channel 'up' or 'dw' 
            ####   (works only with QE, and you need irrep>=1.5.3 installed. Example:
            ####     bands=banduppy.BandStructure(code="espresso", prefix="bulk_Si",spin_channel='up')   # or 'dw'
            ####   examples for other codes are:
            ####  VASP:
            ####      bands=banduppy.BandStructure(fWAV='WAVECAR',fPOS='POSCAR',spinor=False,code='vasp')
            ####  Abinit:
            ####      bands=banduppy.BandStructure(fWFK='mysystem_WFK',code='abinit')
            ####  Files preparedfor Wannier90 (.eig, .win, UNK* ):
            ####      bands=banduppy.BandStructure(prefix='nbcosb',code='wannier90')
            #####   Other parameters may be used (..,Ecut=.,IBstart=..,IBend=..,kplist=..,EF=..)

        except Exception as err:
            raise err
            print("error reading  bandstructure '{}' \n calculating it".format(err))
            pw_file="bulk_Si"
            shutil.copy("input/POSCAR_Si_SC","./POSCAR")
            shutil.copy("input/POTCAR","./POTCAR")
            shutil.copy("input/KPOINTS_scf","./KPOINTS")
            with open("INCAR","w") as f:
                f.write(open("input/INCAR_scf","r").read().format(LSORBIT = "T" if spinorbit else "F"))
            scf_run=run(vasp,stdout=open("out-scf.txt","w"))
            shutil.copy("OUTCAR","./OUTCAR_scf")
            with open("INCAR","w") as f:
                f.write(open("input/INCAR_nscf","r").read().format(LSORBIT = "T" if spinorbit else "F", NBANDS = 96 if spinorbit else 48))
            f = open("KPOINTS","w")
            f.write("Kpoints needed for unfolding on the path \n")
            kpointsPBZ = kpointsPBZ.split("\n")
            f.write(kpointsPBZ[0]+"\nrec \n"+"\n".join(kpointsPBZ[1:])+"\n")
            f.close()
            bands_run=run(vasp,stdout=open("out-bands.txt","w"))
            shutil.copy("OUTCAR","./OUTCAR_nscf")
            bands=banduppy.BandStructure(code="vasp", spinor="True",fPOS = "POSCAR",fWAV = "WAVECAR")
        pickle.dump(bands,open("bandstructure.pickle","wb"))

    unfold_path.unfold(bands,break_thresh=0.1,suffix="path")
    unfold.unfold(bands,suffix="GL")
    pickle.dump(unfold_path,open("unfold-path.pickle","wb"))
    pickle.dump(unfold,open("unfold.pickle","wb"))

#now plot the result as fat band
unfold_path.plot(save_file="unfold_fatband.png",plotSC=True,Emin=-20,Emax=20,Ef='auto',fatfactor=50,mode='fatband') 
#or as a colormap
unfold_path.plot(save_file="unfold_density.png",plotSC=True,Emin=-5,Emax=5,Ef='auto',mode='density',smear=0.2,nE=200) 

#or use the data to plot in any other format
data=np.loadtxt("bandstructure_unfolded-path.txt")



