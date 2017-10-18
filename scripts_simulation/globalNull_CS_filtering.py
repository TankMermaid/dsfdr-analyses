import numpy as np
import pandas as pd
import dsfdr

from biom import load_table
from gneiss.util import match
from scipy.stats import sem
import pickle

# input biom table
def convert_biom_to_pandas(table):
    otu_table = pd.DataFrame(np.array(table.matrix_data.todense()).T,
                             index=table.ids(axis='sample'),
                             columns=table.ids(axis='observation'))
    return otu_table

table = load_table('../data/cs.biom')
otu_table = convert_biom_to_pandas(table)


# input mapping file
mapping = pd.read_table("../data/cs.map.txt", sep='\t', header=0, index_col=0)

# choose interested groups for comparison
mapping = mapping.loc[mapping['smoker'].isin([False, True])]

# match biom table with mapping file
mapping, otu_table = match(mapping, otu_table)
labels = np.array((mapping['smoker'] == False).astype(int))
dat = np.transpose(np.array(otu_table))

# normalization
sample_reads = np.sum(dat, axis=0) # colSum: total reads in each sample
norm_length = 10000
dat_norm = dat/sample_reads*norm_length

# calculate FWER (=FDR in this scenario)
def fwer(rej):
    if np.sum(rej) >= 1:
        r = 1
    else:
        r = 0    
    return r  

# filter reads whose sum in all samples
def filtering_sum(data, filterLev):
    otu_sum = np.sum(data, axis=1)
    keep = np.array(otu_sum >= filterLev)
    table = data[keep==True, :]
    return(table)

# simulation parameters
filtlev = [0, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1250, 1500, 1750, 2000]
B = 100000
nSample = 20
same = dat_norm[:, labels==0]
numbact = same.shape[0]

p_bh = []
p_fbh = []
p_ds = []
p_gb = []

err_bh = []
err_fbh = []
err_ds = []
err_gb = []

sd_bh = []
sd_fbh = []
sd_ds = []
sd_gb = []

num_nulls = []
for f in filtlev:

    r_bh = []
    r_fbh = []
    r_ds = []
    r_gb = []
    num_bact = []

    for b in range(B):
        # simulated data
        sim = np.zeros([numbact, nSample*2]) 
        for i in range(numbact):
            sim[i, :] = np.random.choice(same[i, :], nSample*2)
        # simulated labels    
        labels_sim = np.random.randint(2, size=nSample*2)
        healthy = sim[:, labels_sim==0]
        sick = sim[:, labels_sim==1]
        dat_sim = np.hstack((healthy, sick))
        
        # filtering    
        dat_sim = filtering_sum(dat_sim, filterLev=f)
        num_bact.append(dat_sim.shape[0])
        
        # apply FDR methods
        rej_bh = dsfdr.dsfdr(dat_sim, labels_sim, transform_type = 'rankdata', method = 'meandiff',
                             alpha=0.1, numperm=1000, fdr_method ='bhfdr')
        rej_fbh = dsfdr.dsfdr(dat_sim, labels_sim, transform_type = 'rankdata', method = 'meandiff',
                                     alpha=0.1, numperm=1000, fdr_method ='filterBH')
        rej_ds = dsfdr.dsfdr(dat_sim, labels_sim, transform_type = 'rankdata', method = 'meandiff',
                                     alpha=0.1, numperm=1000, fdr_method ='dsfdr')
        rej_gb = dsfdr.dsfdr(dat_sim, labels_sim, transform_type = 'rankdata', method = 'meandiff',
                                     alpha=0.1, numperm=1000, fdr_method ='gilbertBH')
        
        # total sum of fwer
        r_bh.append(fwer(rej_bh[0]))
        r_fbh.append(fwer(rej_fbh[0]))
        r_ds.append(fwer(rej_ds[0]))
        r_gb.append(fwer(rej_gb[0]))

    print('FDR...: %s' %(f)) 
    num_nulls.append(np.mean(num_bact))
    p_bh.append(np.mean(r_bh))  
    p_fbh.append(np.mean(r_fbh))
    p_ds.append(np.mean(r_ds))
    p_gb.append(np.mean(r_gb))

    err_bh.append(sem(r_bh))
    err_fbh.append(sem(r_fbh))
    err_ds.append(sem(r_ds))
    err_gb.append(sem(r_gb))

    sd_bh.append(np.std(r_bh, ddof=1))
    sd_fbh.append(np.std(r_fbh, ddof=1))
    sd_ds.append(np.std(r_ds, ddof=1))
    sd_gb.append(np.std(r_gb, ddof=1))

with open("../results_all/simulation_cs_norm_s20_filterSum_B100k.pkl", "wb") as f:
    pickle.dump((filtlev, B, nSample, num_nulls, p_bh, p_fbh, p_ds, p_gb,
        err_bh, err_fbh, err_ds, err_gb, sd_bh, sd_fbh, sd_ds, sd_gb), f)   
