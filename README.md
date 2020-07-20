# aspx-page-scrape
Scraping an .aspx website only using bs4 and requests. 


Some code that I wrote in the process of learning to handle tricky aspx View States and scrape data succesfully, trying to do it without using Selenium
to make it a bit lighter and easier to run.
The site was www.bernco.gov , as one of early freelance jobs I've worked on. It involved extracting certain parcel data

Hopefully someone tacklink with similar stuff(View States and .aspx pages with requests) can extract value from the code and get an better idea how to complete his task.


Some additional explanations:
__EVENTTARGET - for finding which control caused the postback (next button f.e.)
__VIEWSTATE - used for saving previous states of the page, it's needed for it to be placed in 'data' of the request

0. First there need to be some constant values in the data
1. in order to display the first parcel list get_viewstates() is to be called to extract all viewstates which will then
   be placed in data
2. In order to paginate through parcels get_index() and get_viewstates() need to be called to extract indexes and viewstates
   which will then be placed in the request data




