import datetime
import os
from datetime import date

import requests
import redis

from errbot import BotPlugin, botcmd

COVID_CACHED_PREFIX = 'czechia_covid_cached.'
COVID_PREVIOUS_PREFIX = 'czechia_covid_previous.'
POPULATION = 10_707_839
DT_FORMAT = '%d. %m. %Y'

# API urls
TESTS_URL = 'https://onemocneni-aktualne.mzcr.cz/api/v2/covid-19/testy-pcr-antigenni.json'
OVERVIEW_URL = 'https://onemocneni-aktualne.mzcr.cz/api/v2/covid-19/zakladni-prehled.json'
VACCINATIONS_URL = 'https://onemocneni-aktualne.mzcr.cz/api/v2/covid-19/ockovani.json'


class CovidData:
    date: str
    tests_pcr: int
    tests_antigen: int
    total_infections: int
    active_infections: int
    recoveries: int
    hospitalized: int
    deceased: int
    vaccinations_first_dose: int
    vaccinations_second_dose: int

    @property
    def total_tests(self):
        return self.tests_pcr + self.tests_antigen


class CzechiaCovid(BotPlugin):

    @botcmd
    def covid(self, msg, args):
        current_data = fetch_data()
        cached_data = get_redis_data(COVID_CACHED_PREFIX)

        # Rotate data on new day, cache current day for next rotation
        if cached_data.date != current_data.date:
            save_to_redis(cached_data, COVID_PREVIOUS_PREFIX)
            save_to_redis(current_data, COVID_CACHED_PREFIX)

        previous_data = get_redis_data(COVID_PREVIOUS_PREFIX)

        pcr_comparison = format_comparison(previous_data.tests_pcr, current_data.tests_pcr)
        antigen_comparison = format_comparison(previous_data.tests_antigen, current_data.tests_antigen)
        total_tests_comparison = format_comparison(previous_data.total_tests, current_data.total_tests)

        active_infections_comparison = format_comparison(previous_data.active_infections, current_data.active_infections)
        recoveries_comparison = format_comparison(previous_data.recoveries, current_data.recoveries)
        total_infections_comparison = format_comparison(previous_data.total_infections, current_data.total_infections)

        hospitalized_comparison = format_comparison(previous_data.hospitalized, current_data.hospitalized)
        deceased_comparison = format_comparison(previous_data.deceased, current_data.deceased)

        first_dose_comparison = format_comparison(previous_data.vaccinations_first_dose, current_data.vaccinations_first_dose)
        second_dose_comparison = format_comparison(previous_data.vaccinations_second_dose, current_data.vaccinations_second_dose)

        first_dose_percent = get_population_percentage(current_data.vaccinations_first_dose)
        second_dose_percent = get_population_percentage(current_data.vaccinations_second_dose)

        if not previous_data.date or current_data.date == previous_data.date:
            msg_head = f"**Aktuální situace Covid-19 k datu: {current_data.date}**"

        else:
            msg_head = f"**Aktuální situace Covid-19 k datu: {current_data.date} (ve srovnání s {previous_data.date})**"

        return f"{msg_head}\n" \
               ":nothing:\n" \
               "\n**Testy** :health_worker:\n" \
               f"\tPCR: **{format_number(current_data.tests_pcr)}** {pcr_comparison}\n" \
               f"\tAntigen: **{format_number(current_data.tests_antigen)}** {antigen_comparison}\n" \
               f"\tCelkem: **{format_number(current_data.total_tests)}** {total_tests_comparison}\n" \
               ":nothing:\n" \
               "\n**Infekce** :coronavirus-wink:\n" \
               f"\tAktuálně infikovaných: **{format_number(current_data.active_infections)}** {active_infections_comparison}\n" \
               f"\tUzdravených: **{format_number(current_data.recoveries)}** {recoveries_comparison}\n" \
               f"\tCelkem nakažených: **{format_number(current_data.total_infections)}** {total_infections_comparison}\n" \
               ":nothing:\n" \
               "\n**Méně pozitivní statistiky** :hospital:\n" \
               f"\tHospitalizovaných: **{format_number(current_data.hospitalized)}** {hospitalized_comparison}\n" \
               f"\tÚmrtí: **{format_number(current_data.deceased)}** {deceased_comparison}\n" \
               ":nothing:\n" \
               "\n**Vakcinace** :syringe:\n" \
               f"\tPrvních dávek: **{format_number(current_data.vaccinations_first_dose)}** ≈ {first_dose_percent} populace {first_dose_comparison}\n" \
               f"\tDruhých dávek: **{format_number(current_data.vaccinations_second_dose)}** ≈ {second_dose_percent} populace {second_dose_comparison}\n" \
               f"---\n" \
               f"Zdroj: Ministerstvo Zdravotnictví ČR"


def fetch_data() -> CovidData:
    tests = requests.get(TESTS_URL).json()
    overview = requests.get(OVERVIEW_URL).json()
    vaccinations = requests.get(VACCINATIONS_URL).json()

    data = CovidData()
    data.date = format_date(overview['data'][0]['datum'])
    data.tests_pcr = sum(int(data_point['pocet_PCR_testy']) for data_point in tests['data'])
    data.tests_antigen = sum(int(data_point['pocet_AG_testy']) for data_point in tests['data'])
    data.total_infections = overview['data'][0]['potvrzene_pripady_celkem']
    data.active_infections = overview['data'][0]['aktivni_pripady']
    data.recoveries = overview['data'][0]['vyleceni']
    data.hospitalized = overview['data'][0]['aktualne_hospitalizovani']
    data.deceased = overview['data'][0]['umrti']
    data.vaccinations_first_dose = sum(int(data_point['prvnich_davek']) for data_point in vaccinations['data'])
    data.vaccinations_second_dose = sum(int(data_point['druhych_davek']) for data_point in vaccinations['data'])

    return data


def get_redis_data(prefix: str) -> CovidData:
    data = CovidData()

    for attr_name in data.__annotations__.keys():
        if attr_name != 'date':
            value = int(REDIS_DB.get(prefix + attr_name)) if REDIS_DB.exists(prefix + attr_name) else 0

        else:
            value = str(REDIS_DB.get(prefix + attr_name)) if REDIS_DB.exists(prefix + attr_name) else ''

        data.__setattr__(attr_name, value)

    return data


def save_to_redis(data: CovidData, prefix: str):
    for attr_name, value in data.__dict__.items():
        REDIS_DB.set(prefix + attr_name, value)


def get_population_percentage(num: int):
    return '{:.1%}'.format(num / POPULATION)


def format_date(dt: str) -> str:
    return date.fromisoformat(dt).strftime(DT_FORMAT)


def format_number(number: int) -> str:
    return f'{number:,}'.replace(',', ' ').strip()


def format_comparison(old_value: int, new_value: int) -> str:
    if old_value:
        if difference := new_value - old_value:
            if difference < 0:
                return f'({format_number(difference)})'

            return f'(+{format_number(difference)})'

    return '(beze změny)'


REDIS_DB = redis.Redis(host=os.environ['REDIS_HOST'],
                       port=os.environ['REDIS_PORT'],
                       db=0,
                       charset="utf-8",
                       decode_responses=True)
