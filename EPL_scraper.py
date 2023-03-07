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

warnings.filterwarnings('ignore')

# set up empty dataframe in a list for storage. errors is set up to handle any matches that dont scrape.
dataframe = []
errors = []

start = 74911
stop = 75163 + 1

for match_id in range(start, stop):
    base_url = f'https://www.premierleague.com/match/{match_id}'
    option = Options()
    option.headless = False
    driver = webdriver.Chrome("#########",
                              options=option)
    driver.get(base_url)

    try:
        # click the cookie pop up
        WebDriverWait(driver, 45).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div[2]/div/div/div[2]/div/div/button[1]'))).click()
        # move to stats tab

        element = WebDriverWait(driver, 15).until(EC.element_to_be_clickable(
            (By.XPATH, "//*[@id='mainContent']/div/section[2]/div[2]/div[2]/div[1]/div/div/ul/li[3]")))
        actions = ActionChains(driver)
        actions.move_to_element(element).click().perform()

        date = driver.find_element("xpath",
                                   '/html/body/main/div/section[2]/div[2]/section/div[1]/div/div[1]/div[1]').text

        date = datetime.strptime(date, '%a %d %b %Y').strftime('%d/%m/%Y')

        referee = driver.find_element("xpath",
                                      '/html/body/main/div/section[2]/div[2]/section/div[1]/div/div[1]/div[2]').text

        venue = driver.find_element("xpath",
                                    '/html/body/main/div/section[2]/div[2]/section/div[1]/div/div[1]/div[3]').text

        home_team = driver.find_element("xpath",
                                        '//*[@id="mainContent"]/div/section[2]/div[2]/div[2]/div[2]/section[3]/div[2]/div[2]/table/thead/tr/th[1]/a').text

        away_team = driver.find_element("xpath",
                                        '//*[@id="mainContent"]/div/section[2]/div[2]/div[2]/div[2]/section[3]/div[2]/div[2]/table/thead/tr/th[3]/a').text

        score = driver.find_element("xpath",
                                    '/html/body/main/div/section[2]/div[2]/section/div[3]/div/div/div[1]/div[2]/div/div').text

        home_score = score.split('-')[0]
        away_score = score.split('-')[1]

        half_time_score = driver.find_element("xpath",
                                              '/html/body/main/div/section[2]/div[2]/section/div[3]/div/div/div[2]/div[1]').text

        ht_home_score = half_time_score.split('-')[0]
        ht_away_score = half_time_score.split('-')[1]

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
        # Code to handle the TimeoutException
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

        # Store the data
    match = [date, venue, home_team, away_team, ht_home_score, ht_away_score, home_score, away_score,
             home_stats['possession_%'],
             away_stats['possession_%'], home_stats['shots_on_target'], away_stats['shots_on_target'],
             home_stats['shots'], away_stats['shots'], home_stats['touches'], away_stats['touches'],
             home_stats['passes'], away_stats['passes'], home_stats['tackles'], away_stats['tackles'],
             home_stats['clearances'], away_stats['clearances'], home_stats['corners'], away_stats['corners'],
             home_stats['offsides'], away_stats['offsides'], home_stats['yellow_cards'], away_stats['yellow_cards'],
             home_stats['red_cards'], away_stats['red_cards'], home_stats['fouls_conceded'],
             away_stats['fouls_conceded'], referee]

    dataframe.append(match)
    print("Scraped the match:", match_id, 'Successfully')
    sleep(5)

# Exporting the data
columns = ['date', 'venue', 'home_team', 'away_team', 'ht_home_score', 'ht_away_score', 'home_score',
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

dataset.to_csv('epl_2223.csv', index=False)

print('csv file exported.')
print(f'Number of errors: {len(errors)}')
print('Errors:\n')
print(errors)
