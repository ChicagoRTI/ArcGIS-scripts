import time

import pp.logger.logger
logger = pp.logger.logger.get('pp_log')



class StatsTimer:
    
    MESH_CREATE_END = 0
    FIND_SITES_END = 1
    WRITE_SITES_END = 2
        
    def __init__(self, desc=''):
        self.times = [time.monotonic(), -1, -1]
        self.quantities = [0, 0, 0]
        self.desc = desc
    
    def record (self, i):
        now = time.monotonic()
        self.times[i] = now - self.times[i]
        if i+1 < len(self.times):
            self.times[i+1] = time.monotonic()


   
class StatsAccumulator:
           
    def __init__(self, desc=''):
        self.times = [0,0,0]
        self.t_ttl = 0
        self.quantities = [0, 0, 0]
        self.desc = desc
                    
    def accumulate (self, stats_timer, process_id, oid, mesh_sq_meters, polygon_sq_meters, plantings):
        quantities = [round(mesh_sq_meters),round(polygon_sq_meters), plantings]
        ttl_time = sum(stats_timer.times)
        logger.info  ("{:>2d} {:>12d} {:>8d} {:>8d} {:>6d} {:>10.3f} {:>10.3f} {:>10.3f} {:>10.3f}".format(process_id, oid, *quantities, *stats_timer.times, ttl_time))        
        for i in range (len(self.times)):
            self.times[i] = self.times[i] + stats_timer.times[i]
        for i in range (len(self.quantities)):
            self.quantities[i] = self.quantities[i] + quantities[i]
        self.t_ttl = self.t_ttl + ttl_time


    def add (self, stats_accumulator):
        for i in range (len(self.times)):
            self.times[i] = self.times[i] + stats_accumulator.times[i]
        for i in range (len(self.quantities)):
            self.quantities[i] = self.quantities[i] + stats_accumulator.quantities[i]
        self.t_ttl = self.t_ttl + stats_accumulator.t_ttl
        
        
    def log_accumulation (self, process_id):
        logger.info  ("{:>2d} {:>12d} {:>8d} {:>8d} {:>6d} {:>10.3f} {:>10.3f} {:>10.3f} {:>10.3f}".format(process_id, 0, *self.quantities, *self.times, self.t_ttl))        



    @staticmethod
    def log_header (desc):
        logger.info  ('')
        logger.info  (desc)
        logger.info  ('--------------------')
        logger.info  ("{:>2s} {:>12s} {:>8s} {:>8s} {:>6s} {:>10s} {:>10s} {:>10s} {:>10s}".format('Pr', 'OID', 'Mesh', 'Polygon', 'Plants', 't_Mesh', 't_Plant', 't_Write', 't_Ttl'))

        

    
