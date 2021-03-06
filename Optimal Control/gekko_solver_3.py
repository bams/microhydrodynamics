from gekko import GEKKO
import numpy as np
import matplotlib.pyplot as pl
import matplotlib.colors as colors
import subprocess
import time 
import scipy.integrate as odes
from StokesSingularities import *

IV=[5,5] #Initial position

g=GEKKO(remote=True)

nt = 400 #number of timesteps
g.time=np.linspace(0,100,nt)

#STATUS = 1 implies that the variable is being optimized by the solver
#DCOST is the amount which is added to the cost function when the variable is modified -> this prevents blowup

# These are the coordinates of the passive particle
y1=g.CV(value=IV[0])
y1.LOWER=-100
y1.UPPER=100
y2=g.CV(value=IV[1])
y2.LOWER=-100
y2.UPPER=100

MODE='CARTES'

# This mode is for cartesian coordinates
if MODE=='CARTES': 
    x11=g.Var(value=0,lb=0)
    x12=g.Var(value=1,lb=0)
    x21=g.Var(value=0,lb=0)
    x22=g.Var(value=0,lb=0)

    v11=g.MV(value=0);v11.STATUS=1
    v12=g.MV(value=0);v12.STATUS=1
    v21=g.MV(value=0);v21.STATUS=0
    v22=g.MV(value=0);v22.STATUS=0

    v11.LOWER=-10
    v11.UPPER=10
    v12.LOWER=-10
    v12.UPPER=10
    v21.LOWER=-10
    v21.UPPER=10
    v22.LOWER=-10
    v22.UPPER=10

    g.Equation(x11.dt()==v11)
    g.Equation(x12.dt()==v12)
    g.Equation(x21.dt()==v21)
    g.Equation(x22.dt()==v22)

# Polar Coordinates
if MODE=='POLAR':
    theta1=g.Var(value=0)
    theta2=g.Var(value=np.pi/2)

    x11=g.Intermediate(g.cos(theta1))
    x12=g.Intermediate(g.sin(theta1))
    x21=g.Intermediate(g.cos(theta2))
    x22=g.Intermediate(g.sin(theta2))

    theta1dot=g.MV(value=0);theta1dot.STATUS=1
    theta2dot=g.MV(value=0);theta2dot.STATUS=1
    theta1dot.DCOST=0.1
    theta2dot.DCOST=0.1
    theta1dot.LOWER=-1
    theta1dot.UPPER=1
    theta2dot.LOWER=-1
    theta2dot.UPPER=1

    v11=g.Intermediate(-theta1dot*g.sin(theta1))
    v12=g.Intermediate(theta1dot*g.cos(theta1))
    v21=g.Intermediate(-theta2dot*g.sin(theta2))
    v22=g.Intermediate(theta2dot*g.cos(theta2))

    g.Equation(theta1.dt()==theta1dot)
    g.Equation(theta2.dt()==theta2dot)

# Stokeslet fundamental solution.
def stokeslet(y1,y2,x11,x12,x21,x22,v11,v12,v21,v22):
    r11=y1-x11
    r12=y2-x12
    r21=y1-x21
    r22=y2-x22
    rinvsq1=1/(r11**2+r12**2)
    rinv1=rinvsq1**0.5
    rinvsq2=1/(r21**2+r22**2)
    rinv2=rinvsq2**0.5 
    rv1=r11*v11+r12*v12 
    rv2=r21*v21+r22*v22
    ydot1=rinv1*(v11+rv1*r11*rinvsq1)+rinv2*(v21+rv2*r21*rinvsq2) 
    ydot2=rinv1*(v12+rv1*r12*rinvsq1)+rinv2*(v22+rv2*r22*rinvsq2)
    return 0.1*np.array([ydot1,ydot2])*3/4
def regularized_stokeslet(y1,y2,x11,x12,x21,x22,v11,v12,v21,v22):
    e=0.1
    r11=y1-x11
    r12=y2-x12
    r21=y1-x21
    r22=y2-x22

    r1v1=r11*v11+r12*v12
    r2v2=r21*v21+r22*v22

    r1r1=r11**2+r12**2
    r2r2=r21**2+r22**2

    rinvsq1=1/(r1r1+e**2)
    rinvsq2=1/(r2r2+e**2)

    ydot1=(rinvsq1**(3/2))*(r1r1*v11+2*(e**2)*v11+r1v1*r11) \
        + (rinvsq2**(3/2))*(r2r2*v21+2*(e**2)*v21+r2v2*r21)
    ydot2=(rinvsq1**(3/2))*(r1r1*v12+2*(e**2)*v12+r1v1*r12) \
        + (rinvsq2**(3/2))*(r2r2*v22+2*(e**2)*v22+r2v2*r22) 
    return 0.1*(3/4)*np.array([ydot1,ydot2])

def blakelet(y1,y2,x11,x12,x21,x22,v11,v12,v21,v22):
    r11=y1-x11
    r12=y2-x12
    r21=y1-x21
    r22=y2-x22
    v1v1=g.sqrt(v11**2+v12**2)
    v2v2=g.sqrt(v21**2+v22**2)
    rinvsq1=1/(r11**2+r12**2)
    rinv1=rinvsq1**0.5
    rinvsq2=1/(r21**2+r22**2)
    rinv2=rinvsq2**0.5 
    rv1=r11*v11+r12*v12 
    rv2=r21*v21+r22*v22
    stokeslet1=rinv1*(v11+rv1*r11*rinvsq1)+rinv2*(v21+rv2*r21*rinvsq2) 
    stokeslet2=rinv1*(v12+rv1*r12*rinvsq1)+rinv2*(v22+rv2*r22*rinvsq2)
    
    r_im11=y1-x11
    r_im12=y2+x12
    r_im21=y1-x21
    r_im22=y2+x22
    r_iminvsq1=1/(r_im11**2+r_im12**2)
    r_iminv1=r_iminvsq1**0.5
    r_iminvsq2=1/(r_im21**2+r_im22**2)
    r_iminv2=r_iminvsq2**0.5 
    r_imv1=r_im11*v11+r_im12*v12 
    r_imv2=r_im21*v21+r_im22*v22
    stokeslet_im1=r_iminv1*(v11+r_imv1*r_im11*r_iminvsq1)+r_iminv2*(v21+r_imv2*r_im21*r_iminvsq2) 
    stokeslet_im2=r_iminv1*(v12+r_imv1*r_im12*r_iminvsq1)+r_iminv2*(v22+r_imv2*r_im22*r_iminvsq2)
    dipole_im1=-2*x12*r_iminvsq1*(v1v1*r_im11*r_iminv1-3*r_imv1*r_im11*r_iminv1**3)+2*x22*r_iminvsq2*(v2v2*r_im21*r_iminv2+3*r_imv2*r_im21*r_iminv2**3)
    dipole_im2=-2*x12*r_iminvsq1*(v1v1*r_im12*r_iminv1-3*r_imv1*r_im12*r_iminv1**3)+2*x22*r_iminvsq2*(v2v2*r_im22*r_iminv2+3*r_imv2*r_im22*r_iminv2**3)
    doublet_im1=2*x12**2*r_iminv1**3*(3*(r_imv1*r_im11)*r_iminvsq1-v11)+2*x22**2*r_iminv2**3*(3*(r_imv2*r_im21)*r_iminvsq2-v21)
    doublet_im2=2*x12**2*r_iminv1**3*(3*(r_imv1*r_im12)*r_iminvsq1-v12)+2*x22**2*r_iminv2**3*(3*(r_imv2*r_im22)*r_iminvsq2-v22)
    return 0.25*(3/4)*np.array([stokeslet1+stokeslet_im1+dipole_im1+doublet_im1,stokeslet2+stokeslet_im2+dipole_im2+doublet_im2])

# Dynamical constraints

g.Equation(y1.dt()==blakelet(y1,y2,x11,x12,x21,x22,v11,v12,v21,v22)[0])
g.Equation(y2.dt()==blakelet(y1,y2,x11,x12,x21,x22,v11,v12,v21,v22)[1])

# Cost function
J=g.Var(value=0)

g.Equation(J==g.integral(v11**2+v12**2+v21**2+v22**2))

final = g.Param(np.zeros(nt)); final[-1]=1
g.Minimize(J*final)
#g.Equation(1e3*g.exp(-((y1-x11)**2+(y2-x22)**2+(y1-x21)**2+(y2-x22)**2)) < 1)
g.Minimize(final*1e5*(y1-3)**2)
g.Minimize(final*1e5*(y2-3)**2)

g.options.IMODE = 6  # optimal control
g.options.NODES = 2  # collocation nodes
g.options.SOLVER = 3 # solver
g.options.MAX_ITER = 10000
g.solver_options={'print_info_string yes'}

g.options.COLDSTART = 1
g.solve(disp=True) # Solve

g.options.COLDSTART = 0
g.options.TIME_SHIFT = 0
g.solve(disp=True) # Solve

fig,(ax1,ax2)=pl.subplots(2)
ax1.plot(g.time,y1.value,label='y1')
ax1.plot(g.time,y2.value,label='y2')
ax1.legend()
ax2.plot(g.time,v11.value,label='v11')
ax2.plot(g.time,v12.value,label='v12')
ax2.plot(g.time,v21.value,label='v21')
ax2.plot(g.time,v22.value,label='v22')
ax2.legend()
pl.savefig("optimal_control.png")
#pl.show()
fig2,ax3=pl.subplots(1)
ax3.plot(y1.value,y2.value,label='trajectory')
#pl.show()
counter=0
xx, yy = np.mgrid[0:10:31j,
                  0:10:31j]
def filt(x):
    if x>=1:
        return 1
    elif x<=0:
        return 1e-5
    else:
        return x
while counter < len(g.time):   
    ux = np.zeros_like(xx)
    uy = np.zeros_like(xx)
    uu=np.zeros_like(xx)
    for i in range(0,xx[:,0].size):
        for j in range(0,xx[:,0].size):
            X = np.array([xx[i,j],yy[i,j]])
            #mat = ss.stresslet_tens(x0, X)
            #vel = np.tensordot(Smat, mat)
            vel = 0.25*(3/4)*blakelet_vec(X-np.array([x11.value[counter],x12.value[counter]]), 
                np.array([v11.value[counter],v12.value[counter]]),np.array([-v11.value[counter],-v12.value[counter]]),x12.value[counter])#+\
             #     0.25*(3/4)*blakelet_vec(X-np.array([x21.value[counter],x22.value[counter]]), 
             #   np.array([v21.value[counter],v22.value[counter]]),np.array([-v21.value[counter],-v22.value[counter]]),x22.value[counter])
            #display(vel - ss.stresslet_vec(X-x0, Fvec, evec))
            ux[i,j] = vel[0]
            uy[i,j] = vel[1]
            uu[i,j] = filt(vel[0]**2+vel[1]**2)
    fig = pl.figure()

    ax = fig.add_subplot(111)
    
    Q=ax.quiver(xx.T[:,0],yy.T[0,:],ux.T,uy.T,uu.T)
    fig.colorbar(Q,extend='max')
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.plot(y1.value[0:counter],y2.value[0:counter], label='Passive')
    ax.scatter(y1.value[counter],y2.value[counter],c='b')

    ax.plot(x11.value[0:counter],x12.value[0:counter], label='Active')
    ax.plot(x21.value[0:counter],x22.value[0:counter], label='Active')
    ax.scatter(x11.value[counter],x12.value[counter],c='r')
    #ax.scatter(x21.value[counter],x22.value[counter],c='r')

    ax.set_xlim(-10,10)
    ax.set_ylim(-10,10)
    ax.set_aspect('equal')
    pl.savefig('C:\\Users\\Michael\\Documents\\Code\\Shum\\microhydrodynamics\\Movies\\imgopt3_'+str("%03d"%(counter))+'.png')
    pl.close()
    print(counter)
    counter=counter+1
subprocess.call(['ffmpeg','-y', '-i', 'C:\\Users\\Michael\\Documents\\Code\\Shum\\microhydrodynamics\\Movies\\imgopt3_%03d.png','-c:v', 'libx264', '-pix_fmt', 'yuv420p', 'C:\\Users\\Michael\\Documents\\Code\\Shum\\microhydrodynamics\\Plots\\opt2.mp4'])


def Lin_ODE(t,y,args):
    v11,v12,v21,v22,x11,x12,x21,x22=args
    y1=y[0]
    y2=y[1]
    y_velocity1=(3/4)*blakelet_vec(np.array([y1-x11,y2-x12]),np.array([v11,v12]),np.array([-v11,-v12]),x12)
    #contribution from first active particle
    y_velocity2=(3/4)*blakelet_vec(np.array([y1-x21,y2-x22]),np.array([v21,v22]),np.array([-v21,-v22]),x22)
    #contribution from second active particle
    return y_velocity1+y_velocity2

def lin_solver(v11vals,v12vals,v21vals,v22vals,x11vals,x12vals,x21vals,x22vals,y0,tvals):
    dt=(tvals[-1]-tvals[0])/tvals.size
    trajectory=np.empty((tvals.size,2)) #trajectory of particle
    Solver=odes.ode(Lin_ODE).set_integrator('DOP853',max_step=dt)
    Solver.set_initial_value(y0) 

    print('Solving ODE...')
    for i in range(len(tvals)):
        Solver.set_f_params([v11vals[i],v12vals[i],v21vals[i],v22vals[i],x11vals[i],x12vals[i],x21vals[i],x22vals[i]])
        trajectory[i,:]=np.array(Solver.integrate(Solver.t+dt))   
    return trajectory

fig2 = pl.figure()
trajectory=lin_solver(v11.value,v12.value,v21.value,v22.value,x11.value,x12.value,x21.value,x22.value,IV,g.time)
pl.plot(trajectory[:,0],trajectory[:,1], label = 'Actual Trajectory')
pl.plot(y1.value,y2.value,label='Predicted Trajectory')
pl.legend()
pl.show()
