import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from time import sleep, time
import pandas as pd
import warnings
import numpy as np
from datetime import datetime
import json
import re

warnings.filterwarnings('ignore')

# set up empty dataframe in a list for storage. errors is set up to handle any matches that dont scrape.
dataframe = []
errors = []

api_url = "https://footballapi.pulselive.com/football/fixtures"

params = {
    "comps": "1",
    "compSeasons": "578",
    "teams": "1,2,127,130,131,43,4,6,7,34,10,163,11,12,23,15,18,21,25,38",
    "page": "1",
    "pageSize": "40",
    "sort": "desc",
    "statuses": "C",
    "altIds": "true",
}

headers = {
    'Origin': 'https://www.premierleague.com',
}
match_ids = []
data_list = []
# set the date
current_date = datetime.now()
page = 0

while True:
    params['page'] = page
    data = requests.get(api_url, params=params, headers=headers).json()

    # uncomment this to print all data:
    # print(json.dumps(data, indent=2))

    for c in data['content']:
        team1, team2, ids, date = c['teams'][0]['team']['name'], c['teams'][1]['team']['name'], int(
            c["id"]), datetime.strptime(c['kickoff']['label'].split(',')[0].strip(), '%a %d %b %Y')
        if (current_date - date).days <= 7:
            print(f'{team1:<30} {team2:<30} {int(c["id"])}', date)
            data_list.append([team1, team2, ids, date])
            match_ids.append(ids)
    if page > data['pageInfo']['numPages']:
        break

    page += 1

data = pd.DataFrame(data_list, columns=['home', 'away', 'mid', 'date'])
data.to_csv('full_games_list.csv', index=False)
# reverse order of list to get the first round matches at the beginning.

match_ids.reverse()

for match_id in match_ids:
    base_url = f'https://www.premierleague.com/match/{match_id}'
    option = Options()
    option.headless = True
    driver = webdriver.Chrome("C:/Users/paulc/Documents/PremNet/chromedriver.exe",
                              options=option)

    sleep(15)

    driver.get(base_url)

    try:

        # click the cookie pop up
        WebDriverWait(driver, 45).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div/div[2]/div/div/div[2]/div/div/button[2]'))).click()
        # move to stats tab

        element = WebDriverWait(driver, 15).until(EC.element_to_be_clickable(
            (By.XPATH, "//*[@id='mainContent']/div/section[2]/div[2]/div/div[1]/div/div/ul/li[3]")))

        actions = ActionChains(driver)
        actions.move_to_element(element).click().perform()

        date = driver.find_element("xpath",
                                   '/html/body/main/div/section[2]/div[2]/section/div[1]/div[1]/div[1]').text

        date = datetime.strptime(date, '%a %d %b %Y').strftime('%d-%m-%Y')

        referee = driver.find_element("xpath",
                                      '//*[@id="mainContent"]/div/section[2]/div[2]/section/div[1]/div[1]/div[5]').text

        referee = referee.replace("Ref: ", "")

        home_team = driver.find_element("xpath",
                                        '//*[@id="mainContent"]/div/section[2]/div[2]/section/div[1]/div[2]/div[1]/div[1]/div[1]/a[2]/span[1]').text

        away_team = driver.find_element("xpath",
                                        '//*[@id="mainContent"]/div/section[2]/div[2]/section/div[1]/div[2]/div[1]/div[3]/div[1]/a[2]/span[1]').text

        score = driver.find_element("xpath",
                                    '//*[@id="mainContent"]/div/section[2]/div[2]/section/div[1]/div[2]/div[1]/div[2]/div[1]').text

        home_score = score.split('-')[0].strip()
        away_score = score.split(' - ')[1].rstrip()

        half_time_score = driver.find_element("xpath",
                                              '//*[@id="mainContent"]/div/section[2]/div[2]/section/div[1]/div[2]/div[1]/div[2]/div[2]/span').text

        ht_home_score = half_time_score.split('-')[0].strip()
        ht_away_score = half_time_score.split('-')[1].strip()

        ht_home_score = ht_home_score.replace("Half Time: ", "")

        stats_page = pd.read_html(driver.page_source)

        game_stats = stats_page[-1]

        # sorting the stats

        home_stats = {}
        away_stats = {}

        home_series = game_stats[home_team]
        away_series = game_stats[away_team]
        stats_series = game_stats['Unnamed: 1']

    except NoSuchElementException:
        # handle the exception by skipping this instance
        print("Game was not played, skipping....")

    except KeyError as e:
        driver.quit()
        errors.append(match_id)
        print("Error with match:", match_id)
        sleep(3)
        continue

    except TimeoutException:
        # Code to handle the TimeoutException
        errors.append(match_id)
        print("Timeout occurred while waiting for element to be located.")
        sleep(3)
        continue

    except ValueError:
        # Code to handle the value error
        errors.append(match_id)
        print("Game was not played, skipping....")
        sleep(3)
        continue

    for row in zip(home_series, stats_series, away_series):
        stat = row[1].replace(' ', '_').lower()
        home_stats[stat] = row[0]
        away_stats[stat] = row[2]

    stats_cols = ['possession_%', 'shots_on_target', 'shots', 'touches', 'passes',
                  'tackles', 'clearances', 'corners', 'offsides', 'yellow_cards',
                  'red_cards', 'fouls_conceded']

    for stat in stats_cols:
        if stat not in home_stats.keys():
            home_stats[stat] = 0
            away_stats[stat] = 0

            continue

        # Store the data
    match = [date, home_team, away_team, ht_home_score, ht_away_score, home_score, away_score,
             home_stats['possession_%'],
             away_stats['possession_%'], home_stats['shots_on_target'], away_stats['shots_on_target'],
             home_stats['shots'], away_stats['shots'], home_stats['touches'], away_stats['touches'],
             home_stats['passes'], away_stats['passes'], home_stats['tackles'], away_stats['tackles'],
             home_stats['clearances'], away_stats['clearances'], home_stats['corners'], away_stats['corners'],
             home_stats['offsides'], away_stats['offsides'], home_stats['yellow_cards'], away_stats['yellow_cards'],
             home_stats['red_cards'], away_stats['red_cards'], home_stats['fouls_conceded'],
             away_stats['fouls_conceded'], referee]

    # check if both home_shots and away_shots are zero
    if home_stats['shots'] == 0 and away_stats['shots'] == 0:
        errors.append(match_id)
        print("Game has not scraped correctly")
        sleep(3)

        continue

    dataframe.append(match)
    print("Scraped the match:", match_id, 'Successfully')
    sleep(5)

# Exporting the data
columns = ['date', 'home_team', 'away_team', 'ht_home_score', 'ht_away_score', 'home_score',
           'away_score', 'home_possession_%',
           'away_possession_%', 'home_shots_on_target', 'away_shots_on_target', 'home_shots', 'away_shots',
           'home_touches', 'away_touches', 'home_passes', 'away_passes',
           'home_tackles', 'away_tackles', 'home_clearances', 'away_clearances', 'home_corners', 'away_corners',
           'home_offsides', 'away_offsides', 'home_yellow_cards', 'away_yellow_cards', 'home_red_cards',
           'away_red_cards',
           'home_fouls', 'away_fouls', 'referee']

dataset = pd.DataFrame(dataframe, columns=columns)

# turn to int

columns_to_convert = ['ht_home_score', 'ht_away_score', 'home_score', 'away_score', 'home_possession_%',
                      'away_possession_%', 'home_shots_on_target', 'away_shots_on_target', 'home_shots', 'away_shots',
                      'home_touches', 'away_touches', 'home_passes', 'away_passes',
                      'home_tackles', 'away_tackles', 'home_clearances', 'away_clearances', 'home_corners',
                      'away_corners',
                      'home_offsides', 'away_offsides', 'home_yellow_cards', 'away_yellow_cards', 'home_red_cards',
                      'away_red_cards', 'home_fouls', 'away_fouls']

for col in columns_to_convert:
    dataset[col] = dataset[col].astype(int)
    dataset[col] = dataset[col].fillna(0)

# turn possession stats to percentages

dataset[['home_possession_%', 'away_possession_%']] = dataset[['home_possession_%', 'away_possession_%']].div(
    100).round(2)

teams_dict = {'Manchester United': 'Manchester United',
              'Brighton & Hove Albion': 'Brighton',
              'West Bromwich Albion': 'West Brom',
              'AFC Bournemouth': 'Bournemouth',
              'Newcastle United': 'Newcastle United',
              'Huddersfield Town': 'Huddersfield',
              'Leicester City': 'Leicester',
              'Manchester City': 'Man City',
              'Stoke City': 'Stoke',
              'Swansea City': 'Swansea',
              'Tottenham Hotspur': 'Tottenham',
              'West Ham United': 'West Ham',
              'Wolverhampton Wanderers': 'Wolverhampton Wanderers',
              'Nottingham Forest': 'Nottingham Forest',
              'Leeds United': 'Leeds'}

for key, value in dataset['home_team'].iteritems():
    dataset['home_team'] = dataset['home_team'].apply(lambda x: teams_dict.get(x, x))

for key, value in dataset['away_team'].iteritems():
    dataset['away_team'] = dataset['away_team'].apply(lambda x: teams_dict.get(x, x))

dataset.to_csv('epl_2324_new.csv', index=False)

print('csv file exported.')
print(f'Number of errors: {len(errors)}')
print('Errors:\n')
print(errors)


for match_id in errors:
    if len(errors) <= 0:
        break
    else:
        base_url = f'https://www.premierleague.com/match/{match_id}'
    option = Options()
    option.headless = True
    driver = webdriver.Chrome("C:/Users/paulc/Documents/PremNet/chromedriver.exe",
                              options=option)

    driver.get(base_url)

    sleep()

    try:
        # click the cookie pop up
        WebDriverWait(driver, 45).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div/div[2]/div/div/div[2]/div/div/button[2]'))).click()
        # move to stats tab
        element = WebDriverWait(driver, 15).until(EC.element_to_be_clickable(
            (By.XPATH, "//*[@id='mainContent']/div/section[2]/div[2]/div/div[1]/div/div/ul/li[3]")))
        actions = ActionChains(driver)
        actions.move_to_element(element).click().perform()

        date = driver.find_element("xpath",
                                   '/html/body/main/div/section[2]/div[2]/section/div[1]/div[1]/div[1]').text

        date = datetime.strptime(date, '%a %d %b %Y').strftime('%d-%m-%Y')

        referee = driver.find_element("xpath",
                                      '//*[@id="mainContent"]/div/section[2]/div[2]/section/div[1]/div[1]/div[5]').text

        referee = referee.replace("Ref: ", "")

        home_team = driver.find_element("xpath",
                                        '//*[@id="mainContent"]/div/section[2]/div[2]/section/div[1]/div[2]/div[1]/div[1]/div[1]/a[2]/span[1]').text

        away_team = driver.find_element("xpath",
                                        '//*[@id="mainContent"]/div/section[2]/div[2]/section/div[1]/div[2]/div[1]/div[3]/div[1]/a[2]/span[1]').text

        score = driver.find_element("xpath",
                                    '//*[@id="mainContent"]/div/section[2]/div[2]/section/div[1]/div[2]/div[1]/div[2]/div[1]').text

        home_score = score.split('-')[0].strip()
        away_score = score.split(' - ')[1].rstrip()

        half_time_score = driver.find_element("xpath",
                                              '//*[@id="mainContent"]/div/section[2]/div[2]/section/div[1]/div[2]/div[1]/div[2]/div[2]/span').text

        ht_home_score = half_time_score.split('-')[0].strip()
        ht_away_score = half_time_score.split('-')[1].strip()

        ht_home_score = ht_home_score.replace("Half Time: ", "")

        stats_page = pd.read_html(driver.page_source)

        game_stats = stats_page[-1]

        # sorting the stats

        home_stats = {}
        away_stats = {}

        home_series = game_stats[home_team]
        away_series = game_stats[away_team]
        stats_series = game_stats['Unnamed: 1']

    except NoSuchElementException:
        # handle the exception by skipping this instance
        print("Game was not played, skipping....")

    except KeyError as e:
        driver.quit()
        errors.append(match_id)
        print("Error with match:", match_id)
        sleep(3)
        continue

    except TimeoutException:
        # Code to handle the TimeoutException
        errors.append(match_id)
        print("Timeout occurred while waiting for element to be located.")
        sleep(3)
        continue

    except ValueError:
        # Code to handle the value error
        errors.append(match_id)
        print("Game was not played, skipping....")
        sleep(3)
        continue

    for row in zip(home_series, stats_series, away_series):
        stat = row[1].replace(' ', '_').lower()
        home_stats[stat] = row[0]
        away_stats[stat] = row[2]

    stats_cols = ['possession_%', 'shots_on_target', 'shots', 'touches', 'passes',
                  'tackles', 'clearances', 'corners', 'offsides', 'yellow_cards',
                  'red_cards', 'fouls_conceded']

    for stat in stats_cols:
        if stat not in home_stats.keys():
            home_stats[stat] = 0
            away_stats[stat] = 0

            continue

        # Store the data
    match = [date, home_team, away_team, ht_home_score, ht_away_score, home_score, away_score,
             home_stats['possession_%'],
             away_stats['possession_%'], home_stats['shots_on_target'], away_stats['shots_on_target'],
             home_stats['shots'], away_stats['shots'], home_stats['touches'], away_stats['touches'],
             home_stats['passes'], away_stats['passes'], home_stats['tackles'], away_stats['tackles'],
             home_stats['clearances'], away_stats['clearances'], home_stats['corners'], away_stats['corners'],
             home_stats['offsides'], away_stats['offsides'], home_stats['yellow_cards'], away_stats['yellow_cards'],
             home_stats['red_cards'], away_stats['red_cards'], home_stats['fouls_conceded'],
             away_stats['fouls_conceded'], referee]

    # check if both home_shots and away_shots are zero
    if home_stats['shots'] == 0 and away_stats['shots'] == 0:
        errors.append(match_id)
        print("Game has not scraped correctly")
        sleep(3)

        continue

    dataframe.append(match)
    print("Scraped the match:", match_id, 'Successfully')
    sleep(5)

# Exporting the data
columns = ['date', 'home_team', 'away_team', 'ht_home_score', 'ht_away_score', 'home_score',
           'away_score', 'home_possession_%',
           'away_possession_%', 'home_shots_on_target', 'away_shots_on_target', 'home_shots', 'away_shots',
           'home_touches', 'away_touches', 'home_passes', 'away_passes',
           'home_tackles', 'away_tackles', 'home_clearances', 'away_clearances', 'home_corners', 'away_corners',
           'home_offsides', 'away_offsides', 'home_yellow_cards', 'away_yellow_cards', 'home_red_cards',
           'away_red_cards',
           'home_fouls', 'away_fouls', 'referee']

dataset = pd.DataFrame(dataframe, columns=columns)

# turn to int

columns_to_convert = ['ht_home_score', 'ht_away_score', 'home_score', 'away_score', 'home_possession_%',
                      'away_possession_%', 'home_shots_on_target', 'away_shots_on_target', 'home_shots', 'away_shots',
                      'home_touches', 'away_touches', 'home_passes', 'away_passes',
                      'home_tackles', 'away_tackles', 'home_clearances', 'away_clearances', 'home_corners',
                      'away_corners',
                      'home_offsides', 'away_offsides', 'home_yellow_cards', 'away_yellow_cards', 'home_red_cards',
                      'away_red_cards', 'home_fouls', 'away_fouls']

for col in columns_to_convert:
    dataset[col] = dataset[col].astype(int)
    dataset[col] = dataset[col].fillna(0)

# turn possession stats to percentages

dataset[['home_possession_%', 'away_possession_%']] = dataset[['home_possession_%', 'away_possession_%']].div(
    100).round(2)

teams_dict = {'Manchester United': 'Manchester United',
              'Brighton & Hove Albion': 'Brighton',
              'West Bromwich Albion': 'West Brom',
              'AFC Bournemouth': 'Bournemouth',
              'Newcastle United': 'Newcastle United',
              'Huddersfield Town': 'Huddersfield',
              'Leicester City': 'Leicester',
              'Manchester City': 'Man City',
              'Stoke City': 'Stoke',
              'Swansea City': 'Swansea',
              'Tottenham Hotspur': 'Tottenham',
              'West Ham United': 'West Ham',
              'Wolverhampton Wanderers': 'Wolverhampton Wanderers',
              'Nottingham Forest': 'Nottingham Forest',
              'Leeds United': 'Leeds'}

for key, value in dataset['home_team'].iteritems():
    dataset['home_team'] = dataset['home_team'].apply(lambda x: teams_dict.get(x, x))

for key, value in dataset['away_team'].iteritems():
    dataset['away_team'] = dataset['away_team'].apply(lambda x: teams_dict.get(x, x))

epl_df = pd.read_csv('epl_2324csv')

new_df = pd.concat([epl_df,dataset],axis=0).sort_values("date",ascending=True)
new_df.to_csv('epl_2324.csv', index=False)

print('csv file exported.')
print(f'Number of errors: {len(errors)}')
print('Errors:\n')
print(errors)
