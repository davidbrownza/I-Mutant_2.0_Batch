#!/usr/bin/env python

import os, sys, argparse, subprocess, datetime, time

def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False 


def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False 


class Imutant2Result:
    
    def __init__(self, name, energy_change, description, reliability_index, ph, temp):
        self.name = name
        self.energy_change = energy_change
        self.description = description
        self.reliability_index = reliability_index
        self.ph = ph
        self.temp = temp
    
    def __str__(self):
        return "%s\t%s\t%s\t%s\t%s \t%s" % (self.name, self.energy_change, self.description, self.reliability_index, self.ph, self.temp)
    
    
class Imutant2:
    
    def __init__(self, mode, seq=None, pdb=None, dssp=None, chain=None, pos=None, new_res=None, ph=None, temp=None):
        self.mode = mode
        self.seq = seq
        self.pdb = pdb
        self.dssp = dssp
        self.chain = chain
        self.pos = pos
        self.new_res = new_res
        self.ph = ph
        self.temp = temp
        self.results = None


    def validate(self):
        if self.mode == "-seq" or self.mode == "-seqv":
            assert os.path.exists(self.seq), "sequence file does not exist"
            
        elif self.mode == "-pdb" or self.mode == "-pdbv":
            assert os.path.exists(self.pdb), "PDB file does not exist"
            assert os.path.exists(self.dssp), "DSSP file does not exist"
            assert self.chain is not None, "chain cannot be null"
        
        else:
            raise Exception("first arg should be one of -seq, -seqv, -pdb or -pdbv")
        
        assert is_integer(self.pos), "position must be an integer"
        assert self.new_res.isalpha(), "new residue '%s' must be a letter character" % self.new_res
        assert self.ph == None or is_float(self.ph), "PH must be a number"
        assert self.temp == None or is_float(self.temp), "temperature must be a number"
    
    
    def compile_command(self):
        imutant_exe = os.path.join("${IMUTANTHOME}", "I-Mutant2.0.py")
        
        if self.mode == "-seq" or self.mode == "-seqv":
            command = "python -O %s %s %s %s %s" % (
                    imutant_exe, self.mode, self.seq, self.pos, self.new_res
                )
        elif self.mode == "-pdb" or self.mode == "-pdbv":
            command = "python -O %s %s %s %s %s %s %s" % (
                    imutant_exe, self.mode, self.pdb, self.dssp, self.chain, self.pos, self.new_res
                )
        else:
            raise Exception("Mode should be one of -seq, -seqv, -pdb or -pdbv\n")
        
        if self.ph is not None:
            command += " %s" % self.ph
            
            if self.temp is not None:
                command += " %s" % self.temp
            
        return command
    
    
    def parse_result(self, out, err):
        sys.stderr.write(err)
        
        scores = []
        started = False
        
        lines = out.split("\n")
        for line in lines:
            if not started and line.startswith("      Position"):
                started = True
            
            elif started and len(line) > 0:
                pos = line[7:14].strip()
                wild_type = line[18:19].strip()
                new_type = line[22:24].strip()
                    
                name = "%s%s%s" % (wild_type, pos, new_type)
                
                if self.mode == "-seq":
                    energy_change = "n/a "
                    description = line[28:36].strip()
                    reliability_index = line[39:40].strip()
                    ph = line[43:46].strip()
                    temp = line[49:51].strip()
                
                elif self.mode == "-seqv":
                    energy_change = line[27:32].strip()
                    description = "n/a     "
                    reliability_index = "n/a"
                    ph = line[34:38].strip()
                    temp = line[40:43].strip()
                
                elif self.mode == "-pdb":
                    energy_change = "n/a "
                    description = line[28:36].strip()
                    reliability_index = line[39:40].strip()
                    ph = line[43:46].strip()
                    temp = line[49:51].strip()
                
                elif self.mode == "-pdbv":
                    energy_change = line[27:32].strip()
                    description = "n/a     "
                    reliability_index = "n/a"
                    ph = line[34:38].strip()
                    temp = line[40:43].strip()
                
                scores.append(Imutant2Result(name, energy_change, description, reliability_index, ph, temp))
            
            elif started:
                break
        
        self.results = scores
        return self.results


    def submit(self):
        cmd = self.compile_command()
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process


    @staticmethod
    def load_from_file(path):
        params = []
        with open(path, 'r') as f:
            count = 0
            for line in f:
                try:
                    count += 1
                    
                    arr = line.strip('\n').split("|")
                    
                    mode = arr[0]
                    ph = None
                    temp = None
                    
                    if mode == "-seq" or mode == "-seqv":
                        assert len(arr) > 3, "not enough parameters were provided"
                    
                        if len(arr) > 4:
                            ph = arr[4]
                            
                            if len(arr) > 5:
                                temp = arr[5]
                        
                        im = Imutant2(mode=mode, seq=arr[1], pos=arr[2], 
                            new_res=arr[3], ph=ph, temp=temp)
                        
                        im.validate()
                        
                        params.append(im)
                    
                    elif mode == "-pdb" or mode == "-pdbv":
                        assert len(arr) > 5, "not enough parameters were provided"
                        
                        if len(arr) > 6:
                            ph = arr[6]
                            
                            if len(arr) > 7:
                                temp = arr[7]
                        
                        im = Imutant2(mode=mode, pdb=arr[1], dssp=arr[2], chain=arr[3],
                            pos=arr[4], new_res=arr[5], ph=ph, temp=temp)
                        
                        im.validate()
                        
                        params.append(im)
                        
                    else:
                        raise Exception("first arg should be one of -seq, -seqv, -pdb or -pdbv")
                        
                except Exception, ex:
                    sys.stderr.write("Line %d: %s\n" % (count, str(ex)))
                
        return params


def kill_process(proc):
    try:
        proc.kill()
    except OSError:
        # can't kill a dead proc
        pass


def run(params, num_processes=1):
    processes = []
    results = {}
    
    submitted = 0
    completed = 0
    while completed < len(params):
        
        if len(processes) < num_processes and submitted < len(params):
            # spawn a new process
            im = params[submitted]
            proc = im.submit()
            
            processes.append((im, proc))
            
            submitted += 1
        
        else:
            # monitor running processes
            while len(processes) >= num_processes or submitted == len(params):
                
                for process in processes:
                    proc = process[1]
                    
                    # if process completed
                    if proc.poll() is not None:
                        out, err = proc.communicate()
                        
                        im = process[0]
                        
                        #add scores to the result dictionary
                        scores = im.parse_result(out, err)
                        for score in scores:
                            score_key = "%s:%s" % (score.name, im.mode[1:4])
                            
                            if score_key in results:
                                if im.mode in ["-seq", "-pdb"]:
                                    results[score_key].description = score.description
                                    results[score_key].reliability_index = score.reliability_index
                                
                                elif im.mode in ["-seqv", "-pdbv"]:
                                    results[score_key].energy_change = score.energy_change
                            
                            else:
                                results[score_key] = score
                        
                        # kill process
                        kill_process(proc)
                        
                        completed += 1
                
                processes = [process for process in processes if process[1].returncode is None]
                if len(processes) == 0:
                    break
                
                # wait for a second before checking again
                time.sleep(1)
    
    return results
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submit multiple mutations to I-Mutant 2.0")
    
    parser.add_argument('--processes', type=int, help='Number of processes to run in parallel')
    parser.add_argument('--input', help='A batch input file consisting of the parameters to submit to the I-Mutant 2.0 script')
    parser.add_argument('--output', help='Output file name')
    
    args = parser.parse_args(sys.argv[1:])
    
    params = Imutant2.load_from_file(args.input)
    
    num_processes = min(len(params), args.processes) 
    
    start_time  = datetime.datetime.now()
    
    results = run(params, num_processes)
    
    end_time = datetime.datetime.now()
    
    print end_time - start_time
    
    with open(args.output, "w") as f:
        f.write("#Key      \tName\tDDG \tStability\tRI\tpH  \tTemp")
        
        for k,v in results.iteritems():
            f.write("\n%s\t%s" % (k, v))
    
