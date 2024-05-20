import inv.merge_records
import datetime as dt

def run():
    print (f"{dt.datetime.now():%c}: Started")  
    
    inv.merge_records.run()
    
    print (f"{dt.datetime.now():%c}: Finished")
    return




if __name__ == '__main__':
    run()

