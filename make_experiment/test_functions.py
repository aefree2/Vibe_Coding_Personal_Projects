from get_functions import find_functions

if __name__ == "__main__":
    #https://github.com/jbdamask/scratch/blob/8e927149a250e44f09756f7fdf6d7db04b2a2623 scratch/TOOLS/invoice-creator/backend/worklog_processor.py
    find_functions("https://github.com/jbdamask/scratch/", "8e927149a250e44f09756f7fdf6d7db04b2a2623", "scratch", "../fn_test_files/worklog_proscessor.py", path="test_fn.csv") #confirmed that it will get top level files. 
    find_functions("https://github.com/jbdamask/scratch", "8e927149a250e44f09756f7fdf6d7db04b2a2623", "scratch", "../fn_test_files/main.py", path="test_fn.csv") #confirmed that it will get top level files. 

   #found the error
   #so failed file writing actually works correctly