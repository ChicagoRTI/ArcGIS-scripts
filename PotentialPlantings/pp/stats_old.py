import time

import pp.logger
logger = pp.logger.get('pp_log')

LOG_DETAILS_FREQUENCY = 1000

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
        self.count = 0
        self.times = [0,0,0]
        self.t_ttl = 0
        self.quantities = [0, 0, 0]
        self.desc = desc
                    
    def accumulate (self, stats_timer, process_id, oid, mesh_sq_meters, polygon_sq_meters, plantings):
        quantities = [mesh_sq_meters, polygon_sq_meters, plantings]
        ttl_time = sum(stats_timer.times)
        self.count = self.count + 1
        
        if LOG_DETAILS_FREQUENCY > 0 and self.count % LOG_DETAILS_FREQUENCY == 0:
            acres_per_second = polygon_sq_meters/ttl_time if ttl_time != 0 else 0
            logger.info  ("{:>2s} {:>12s} {:>12.3f} {:>12.3f} {:>9d} {:>10.3f} {:>9.3f} {:>9.3f} {:>10.3f} {:>7.1f} {:>8d}".format(str(process_id), str(oid), *quantities, *stats_timer.times, ttl_time, acres_per_second, self.count))        
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
        pid = '' if process_id is None else str(process_id)
        acres_per_second = self.quantities[1]/self.t_ttl
        logger.info  ("{:>2s} {:>12s} {:>12.3f} {:>12.3f} {:>9d} {:>10.3f} {:>9.3f} {:>9.3f} {:>10.3f} {:>7.1f} {:>8d}".format(pid, '', *self.quantities, *self.times, self.t_ttl, acres_per_second, self.count))        



    @staticmethod
    def log_header (desc):
        logger.info  ('')
        logger.info  (desc)
        logger.info  ('--------------------')
        logger.info  ("{:>2s} {:>12s} {:>12s} {:>12s} {:>9s} {:>10s} {:>9s} {:>9s} {:>10s} {:>7s} {:>8s}".format('',      '', 'Mesh ',  'Site',       '',  'Mesh   ',  'Tree   ', 'Write  ', 'Total  ', 'Acres/', 'Total'))
        logger.info  ("{:>2s} {:>12s} {:>12s} {:>12s} {:>9s} {:>10s} {:>9s} {:>9s} {:>10s} {:>7s} {:>8s}".format('Pr', 'OID', 'Acres',  'Acres', 'Trees',  'Seconds',  'Seconds', 'Seconds', 'Seconds', 'Second', 'Sites'))
