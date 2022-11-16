from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import re
import requests
import os
from time import sleep
from datetime import datetime
import mariadb
startYear = 2019
endYear = 2022
valleyDivision = ["Grand Valley", "Crestwood", "Independence", "Wickliffe", "Cardinal", "Kirtland", "Berkshire", "Trinity", "Richmond"]
chagrinDivision = ["West Geauga", "Hawken", "Orange", "Edgewood", "Chagrin Falls", "Geneva", "Beachwood", "Perry", "Lakeside", "Harvey"]
#Little custom exception I made to break out of a nested loop
class ListTooLong(Exception):
	pass
#Checks if a string has at least one number in it
def hasNumber(string):
	return any(char.isdigit() for char in string)
#Calculates the average time of a cross country race primarily given a list of strings of times
def averageTimeCalculator(times):
	timeList = []
	#Splits the time into minutes and seconds and averages them seperately then puts them back together
	for t in times:
		timeSplit = t.split(":")
		minutes = int(timeSplit[0])*60
		seconds = int(timeSplit[1])
		time = minutes+seconds
		timesList.append(time)
	averageTime = sum(timeList)/len(timeList)
	averageTimeMinutes = math.floor(averageTime/60)
	averageTimeSeconds = round(averageTime%60, 4)
	if (averageTimeSeconds<10):
		return str(averageTimeMinutes)+":0"+str(averageTimeSeconds)
	else:
		return str(averageTimeMinutes)+":"+str(averageTimeSeconds)
#Checks if a given link would contain the results of a boys division 2 5k cross country race, otherwise returns false
def checkLink(link, y, t):
	if (link=="Varsity Boys" or link=="\"Completed\" Results" or link=="Boys D2 Varsity" or link=="D2 Varsity" or link=="Varsity Results" or link=="boys varsity" or link=="Varsity D2/3 Results"):
		return True
	elif (link=="Boys DI/DII" or link=="D2 Boys" or link=="Boys Results" or link=="Small School Division" or link=="HS Boys Varsity" or link=="Region 5" or link=="HS Boys"):
		return True
	elif (link=="D2/D3 Boys" or link=="Boys - Division II" or link=="HS Boys D2" or link=="Small School Boys" or link=="HS Boys D2-3" or link=="HS Boys Blue" or link=="Boys - Div II"):
		return True
	elif (link=="Varsity Boys Blue" or link=="D2 Varsity Boys" or link=="Boys Varsity" or link=="Men\'s Results" or link=="DI and DII Boys" or link=="Full HS Results" or link=="D2 Results"):
		return True
	elif (link=="High School Results" or link=="HS Boys Results" or link=="Boys Varsity B" or link=="Division 2 Boys HS" or link=="HS Results" or link=="Division 2 Results"):
		return True
	elif (link=="Division 2-3 HS Results" or link=="HS Boys - Small School" or link=="HS Boys DII&III Results" or link=="HS Boys Blue Division" or link=="Boys HS 5K Run Varisity"):
		return True
	elif (link=="Boys Gold Varsity" or link=="HS Boys Blue Results" or link=="HS Individual Results" or link=="HS Mens Results" or link=="High School Boys" or link=="Varsity HS Results"):
		return True
	elif (y==2019 and (t=="Gilmour" or t=="Berkshire") and (link=="Division 3" or link=="Division 3 Results" or link=="D3 Results" or link=="Division 3 HS Results")):
		return True
	elif ((t=="Garfield" and link=="HS Boys - County") or (t!="Garfield" and link=="HS Boys - Metro")):
		return True
	elif ((t!="VASJ" and link=="Varsity Boys - Blue") or (t=="VASJ" and link=="Varsity Boys - White")):
		return True
	elif (y<2019 and t=="Hawken"  and (link=="Varsity Boys - Valley" or link=="Boys Valley" or link=="boys valley varsity" or link=="Valley Division")):
		return True
	elif ((t in valleyDivision) and (link=="Varsity Boys - Valley" or link=="Boys Valley" or link=="boys valley varsity" or link=="Valley Division" or link=="Valley Varsity Boys")):
		return True
	elif ((t in chagrinDivision) and (link=="Varsity Boys - Chagrin" or link=="boys chagrin varsity" or link=="Boys Chagrin" or link=="boys chagrin varsity" or link=="Chagrin Division" or link=="Chagrin Varsity Boys")):
		return True
	else:
		return False
#Uses a weather API to retrieve some historical weather readings based on location and time and returns the resulting list
def getWeatherData(location, date, time):
	weatherData = []
	city = location.split(",")[0]
	state = location.split(",")[1].strip()
	response = requests.get("https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"+city+"%2C%20"+state+"/"+date+"T"+time+"/"+date+"T"+time+"?unitGroup=metric&include=hours&key=U36K99V5F9CQN7A6LPRAT3SYP&contentType=json&elements=datetime,temp,humidity,dew,precip,windspeed,cloudcover")
	data = response.json()
	for item in data["days"][0]["hours"]:
		if (item["datetime"]==time):
			weatherData.append(item["temp"])
			weatherData.append(item["humidity"])
			weatherData.append(item["dew"])
			weatherData.append(item["precip"])
			weatherData.append(item["windspeed"])
			weatherData.append("NULL")
			weatherData.append(item["cloudcover"])
	return weatherData
#Returns the team name and ID of the teams in the Madison 2022 District for D2 Bots
def getTeams():
	teams = []
	request = Request("https://oh.milesplit.com/meets/501164-ohsaa-division-2-district-madison-2022/teams")
	page = urlopen(request)
	soup = BeautifulSoup(page, "lxml")
	for tag in soup.find_all("td", "name"):
			urlString = str(tag.find("a").get("href"))
			teamName = str(tag.find("a").text.strip())
			teamNumber = [int(x) for x in urlString if x.isdigit()]
			cNum = ""
			for n in teamNumber:
				cNum+=str(n)
			teams.append([int(cNum), teamName])
	return teams
#Given the team and the year, returns a list fo the meets and the link to the meet info
def getMeets(team, year):
	meetsData = []
	response = requests.get("https://oh.milesplit.com/api/v1/teams/"+str(team[0])+"/schedules?season=cc&year="+str(year))
	meetData = response.json()
	for x in meetData["data"]:
		for y in range(len(meetData["data"][x])):
			for d in range(len(meetData["data"][x][y]["items"])):
				name = meetData["data"][x][y]["items"][d]["name"]
				meetLink = meetData["data"][x][y]["items"][d]["link"]
				meetsData.append([name, meetLink])
	return meetsData
#Gets data about the meet
def getMeetResults(meetData, year, team):
	#Finds the name of the team we are looking to get results for, sometimes is abbreviated so it identified the part most likely to appear in the results
	teamName = team[1].split()
	if (len(teamName)==1):
		team[1] = team[1]
	elif (teamName[0].__contains__(".")):
		team[1] = teamName[1]
	elif (teamName[1].__contains__(".")):
		if (team[1] == "Lake Cath."):
			team[1] = "Lake Cath"
		else:
			team[1] = teamName[0]
	else:
		if (team[1] == "Chardon NDCL"):
			team[1] = "NDCL"
		elif (team[1] == "Gilmour Academy"):
			team[1] = "Gilmour"
		elif (team[1] == "Jefferson Area"):
			team[1] = "Jefferson"
		team[1] = team[1]
	#Get meet ID from the link
	meetId = meetData[1].split("/")[-1]
	#Changes the meet name into something that would appear in the meet link
	name = (meetData[0]).lower()
	name = name.replace(" - ", " ")
	name = name.replace(" ", "-")
	name = name.replace("/", "")
	meetLink = meetData[1]+"-"+name+"-"+str(year)+"/results"
	resultsRequest = Request(meetLink)
	resultPage = urlopen(resultsRequest)
	resultSoup = BeautifulSoup(resultPage, "lxml")
	raceLink = None
	results = None
	date = None
	#Loops through all the links on the page and finds the one that has the results we are looking for
	for link in resultSoup.findAll("a"):
		currentLink = link.get("href")
		try:
			linkText = link.contents[0].strip()
		except:
			continue
		if(currentLink.__contains__("https://www.milesplit")):
			continue
		if checkLink(linkText, year, team[1]):
			print(linkText)
			if (currentLink.__contains__("/raw")):
				raceLink = currentLink
			else:
				raceLink = currentLink + "/raw"
	#If we actually find the right link then gather the raw data from the header of the page and the body
	if raceLink is not None:
		resultsRequest = Request(raceLink)
		resultsPage = urlopen(resultsRequest)
		sleep(0.5)
		resultSoup = BeautifulSoup(resultsPage, "lxml")
		sleep(0.5)
		date = resultSoup.find("time").text.strip()
		date = datetime.strptime(date, "%b %d, %Y").isoformat()[:10]
		location = resultSoup.find("div", "venueCity").text.strip()
		results = str(resultSoup.find("div", id="meetResultsBody"))
	else:
		return None
	#If the results contain both boys and girl results then figure out which block of results to use to get the d2 boys varisty
	if (results.__contains__("Girls") or results.__contains__("girls") or results.__contains__("Open") or results.__contains__("open")):
		bSplit = results.split("5K")
		if (len(bSplit)<2):
			bSplit = results.split("5k")
		if (len(bSplit)<2):
			bSplit = results.split("5,000")
		if (len(bSplit)<2):
			bSplit = results.split("5000")
		for b in range(1, len(bSplit)):
			lines = bSplit[b].split("\n")
			prevLines = bSplit[b-1].split("\n")
			if (meetData[0].__contains__("Chagrin Valley Conference")):
				if (team[1] in chagrinDivision):
					if (lines[0].__contains__("Chagrin") and prevLines[-1].__contains__("Boys") and lines[0].__contains__("Varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("chagrin") and prevLines[-1].__contains__("boys") and lines[0].__contains__("varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("Chagrin") and prevLines[-1].__contains__("boys") and lines[0].__contains__("varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("chagrin") and prevLines[-1].__contains__("Boys") and lines[0].__contains__("varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("chagrin") and prevLines[-1].__contains__("boys") and lines[0].__contains__("Varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("Chagrin") and prevLines[-1].__contains__("Boys") and lines[0].__contains__("varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("chagrin") and prevLines[-1].__contains__("Boys") and lines[0].__contains__("Varsity")):
						results = bSplit[b]
						break
				elif (team[1] in valleyDivision):
					if (lines[0].__contains__("Valley") and prevLines[-1].__contains__("Boys") and lines[0].__contains__("Varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("valley") and prevLines[-1].__contains__("boys") and lines[0].__contains__("varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("Valley") and prevLines[-1].__contains__("boys") and lines[0].__contains__("varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("valley") and prevLines[-1].__contains__("Boys") and lines[0].__contains__("varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("valley") and prevLines[-1].__contains__("boys") and lines[0].__contains__("Varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("Valley") and prevLines[-1].__contains__("Boys") and lines[0].__contains__("varsity")):
						results = bSplit[b]
						break
					elif (lines[0].__contains__("valley") and prevLines[-1].__contains__("Boys") and lines[0].__contains__("Varsity")):
						results = bSplit[b]
						break
			else:
				if (team[1]!="Geneva" and lines[0].__contains__("Run") and prevLines[-1].__contains__("Boys") and not lines[0].__contains__("Gray") and not lines[0].__contains__("Open") and not lines[0].__contains__("D1")):
					results = bSplit[b]
					break
				elif (team[1]=="Geneva" and lines[0].__contains__("Run") and prevLines[-1].__contains__("Boys") and lines[0].__contains__("Gray")):
					results = bSplit[b]
					break
				elif ((lines[0].__contains__("Division 2") and prevLines[-1].__contains__("Boys")) or (prevLines[-1].__contains__("High School Boys") and not prevLines[-1].__contains__("Team Results"))):
					results = bSplit[b]
					break
				elif ((lines[0].__contains__("Varsity") and prevLines[-1].__contains__("Boys") and not lines[0].__contains__("D1")) or (prevLines[-1].__contains__("Boys") and prevLines[-1].__contains__("Varsity"))):
					results = bSplit[b]
					break
				elif ((lines[0].__contains__("run") and prevLines[-1].__contains__("boys")) or (lines[0].__contains__("varsity") and prevLines[-1].__contains__("boys"))):
					results = bSplit[b]
					break
				elif ((lines[0].__contains__("Run") and prevLines[-1].__contains__("boys")) or (lines[0].__contains__("Varsity") and prevLines[-1].__contains__("boys"))):
					results = bSplit[b]
					break
				elif ((lines[0].__contains__("run") and prevLines[-1].__contains__("Boys")) or (lines[0].__contains__("varsity") and prevLines[-1].__contains__("Boys"))):
					results = bSplit[b]
					break
		#print(results)
	times = []
	#Go through the lines of results and pick out the ones fro the team we are looking at and that are realistic and not splits or something
	lines = results.split("\n")
	try:
		for line in lines:
			if (line.lower().__contains__(team[1].lower()) and not line.lower().__contains__("total")):
				for item in line.split():
					#Cuts off hour part
					if (len(item.split(":"))>2):
						item = item[2:]
					try:
						if (hasNumber(item) and item.__contains__(":") and int(item.split(":")[0])>13 and int(item.split(":")[0])<30):
							#Limits times gathered to 7
							if (len(times)>=7):
								raise ListTooLong
							else:
								times.append(item)
								print(item)
					except ValueError:
						pass
	except ListTooLong:
		pass
	#If not a full 7 runners ran, then fill the rest of the datatable with NULL values
	while (len(times)<7):
		times.append("NULL")
	return [meetData[0], times, date, location, team[1], meetId]
#Just the SQL command to put the right data about the meet into the data table
def enterMeetData(meetData, c, mydb):
	strCommand = "INSERT INTO MeetData VALUES ('"+meetData[0]+"', '"+meetData[2]+"'"
	nullMark = False
	for data in meetData[6]:
		if (data is None):
			strCommand+=", NULL"
		else:
			strCommand+=", "+str(data)
	strCommand+=", "+meetData[5]+")"
	c.execute(strCommand)
	mydb.commit()
#Same thign as above but for team data about a singular meet
def enterTeamData(meetData, c, mydb):
	strCommand = "INSERT INTO TeamData VALUES ('"+meetData[4]+"', '"+meetData[2]
	nullMark = False
	for time in meetData[1]:
		if (time=="NULL" and not nullMark):
			strCommand+=("', "+time)
			nullMark = True
		elif (time=="NULL" and nullMark):
			strCommand+=(", "+time)
			nullMark = True
		elif (nullMark):
			strCommand+=(", '"+time)
			nullMark = False
		else:
			strCommand+=("', '"+time)
			nullMark = False
	if (nullMark):
		strCommand+=", "+meetData[5]+")"
	else:
		strCommand+="', "+meetData[5]+")"
	c.execute(strCommand)
	mydb.commit()
def main():
	mydb = mariadb.connect(host="localhost", username="stats", password="crossCountry2048", database="statsProject")
	cursor = mydb.cursor()
	#Checks if the necessary tables exist, create them if they don't and clear them if they do and have data in them
	cursor.execute("SHOW tables")
	result = cursor.fetchall()
	meetTableExists = False
	teamTableExists = False
	for r in result:
		if (r[0]=="MeetData"):
			cursor.execute("SELECT * FROM MeetData")
			r = cursor.fetchall()
			if (r!=[]):
				choice = str(input("Data found in MeetData, delete?(Y/n): "))
				if (choice=="Y"):
					cursor.execute("DELETE FROM MeetData")
					mydb.commit()
			meetTableExists = True
		elif (r[0]=="TeamData"):
			cursor.execute("SELECT * FROM TeamData")
			r = cursor.fetchall()
			if (r!=[]):
				choice = str(input("Data found in TeamData, delete?(Y/n): "))
				if (choice=="Y"):
					cursor.execute("DELETE FROM TeamData")
					mydb.commit()
			teamTableExists = True
	if (not meetTableExists):
		cursor.execute("CREATE TABLE MeetData (meetName VARCHAR(255) NOT NULL, meetDate DATE NOT NULL, temp FLOAT, humidity FLOAT, dewPoint FLOAT, precip FLOAT, windspeed FLOAT, windgust FLOAT, cloudcover FLOAT, meetId INT NOT NULL, PRIMARY KEY (meetId))")
		mydb.commit()
	if (not teamTableExists):
		cursor.execute("CREATE TABLE TeamData (teamName VARCHAR(255) NOT NULL, meetDate DATE NOT NULL, runner1 TIME, runner2 TIME, runner3 TIME, runner4 TIME, runner5 TIME, runner6 TIME, runner7 TIME, meetId INT NOT NULL, PRIMARY KEY (meetId))")
		mydb.commit()
	ids = []
	cursor.execute("SELECT meetId FROM MeetData")
	meetIds = cursor.fetchall()
	for id in meetIds[0]:
		ids.append(id[0])
	results = []
	#For all the teams, years, and meets collect data and store it into the database
	teams = getTeams()
	for year in range(startYear, endYear):
		print(str(year)+"\n")
		counter = 1
		for team in teams:
			if (team[1]=="Beaumont" or team[1]=="Kenston" or team[1]=="Collinwood"): #or team[1]=="Ash. Edgewood" or team[1]=="Chagrin Falls" or team[1]=="Berkshire" or team[1]=="Chardon NDCL" or team[1]=="Cle. VASJ"):
				continue
			#elif (team[1]=="Conneaut" or team[1]=="Crestwood" or team[1]=="Gar. Garfield" or team[1]=="Geneva" or team[1]=="Gilmour Academy" or team[1]=="Hawken" or team[1]=="Kenston"):
			#	continue
			#elif (team[1]=="Jefferson Area" or team[1]=="Lake Cath." or team[1]=="Lakeview" or team[1]=="Niles McKinley" or team[1]=="Orange" or team[1]=="Perry" or team[1]=="Ursuline"):
			#	continue
			#elif(team[1]=="War. Champion"):
				continue
			print(team[1]+" "+str(counter)+"/"+str(len(teams))+"\n")
			meets = getMeets(team, year)
			for meet in meets:
				if (meet[0].__contains__("McQuaid") or meet[0].__contains__("Berkshire Early Bird") or meet[0].__contains__("Dick Malloy Invitational")):
					continue
				print(meet[0])
				results = getMeetResults(meet, year, team)
				if results is None:
					print("Link not found")
					continue
				if (results[-1] in ids):
					print("Meet already recorded")
					continue
				#if (not meet[0].__contains__("Night")):
				#	results.append(getWeatherData(results[3], results[2], "10:00:00"))
				#else:
				#	results.append(getWeatherData(results[3], results[2], "21:00:00"))
				#try:
				#	enterTeamData(results, cursor, mydb)
				#	enterMeetData(results, cursor, mydb)
				#except mariadb.IntegrityError:
				#	pass
				print("")
			print("\n")
			counter+=1
		print("\n\n")
	mydb.close()
if __name__=="__main__":
	main()
