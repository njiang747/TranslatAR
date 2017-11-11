"""
Code example for getting languages supported by Microsoft Translator API.
Visit http://docs.microsofttranslator.com/languages.html to view the API reference.
"""

import uuid

import requests

API_BASE_URL = 'https://dev.microsofttranslator.com'
API_SUPPORTED_LANGUAGES_URL = API_BASE_URL + '/languages'


def get_supported_languages(scope=None, locale=None):
    '''Gets supported languages given scope and locale.'''

    # Specify request headers
    # Always include an identifier to identify the request if it should be traced
    headers = {'X-ClientTraceId': str(uuid.uuid4())}
    # If localization of names is desired, specify the target language
    if locale:
        headers['Accept-Language'] = str(locale)

    # Specify query parameters
    # Always include the desired version of the API
    params = {'api-version': '1.0'}
    # Specify specific scopes to get.
    if scope:
        params['scope'] = scope

    response = requests.get(API_SUPPORTED_LANGUAGES_URL, params=params, headers=headers)

    response.raise_for_status()

    return response.json()


class LanguageViewItem(object):
    DisplayName = ''
    Code = ''


class VoiceViewItem(object):
    DisplayName = ''
    Gender = ''
    RegionName = ''
    Code = ''


def list_supported_languages(localizeTo=None):
    data = get_supported_languages('speech,text,tts', localizeTo)

    print('--------------------------------------------------')
    print('List of supported languages for speech recognition')
    print('--------------------------------------------------')

    # Build list of languages to display. For each language show:
    #   * DisplayName: User-friendly name of language
    #   * Code: Language code to use when making API request.
    speechLanguages = []
    for k, v in data['speech'].items():
        speechLanguage = LanguageViewItem()
        speechLanguage.DisplayName = v['name']
        speechLanguage.Code = k
        speechLanguages.append(speechLanguage)

    # Sort languages alphabetically by DisplayName before printing the list
    speechLanguages.sort(key=lambda x: x.DisplayName)
    for speechLanguage in speechLanguages:
        print(speechLanguage.DisplayName)
        print('  API code: %s' % (speechLanguage.Code))
    print('--------------------------------------------------\n')

    print('--------------------------------------------------')
    print('List of supported languages for text translation  ')
    print('with available voices for text-to-speech          ')
    print('--------------------------------------------------')

    # Group available voices by language.
    voicesByPrimaryLanguageCode = {}
    for k, v in data['tts'].items():
        primaryLanguageCode = v['locale'].split('-')[0]
        voice = VoiceViewItem()
        voice.DisplayName = v['displayName']
        voice.Gender = v['gender']
        voice.RegionName = v['regionName']
        voice.Code = k
        voices = voicesByPrimaryLanguageCode.get(v['language'], [])
        voices.append(voice)
        voicesByPrimaryLanguageCode[v['language']] = voices
    # For each primary language, sort the list of voices alphabetically by DisplayName
    for voices in voicesByPrimaryLanguageCode.values():
        voices.sort(key=lambda x: x.DisplayName)

    # Build list of languages to display. For each language show:
    #   * DisplayName: User-friendly name of language
    #   * Code: Language code to use when making API request.
    #   * Voices: List of available voices for text-to-speech
    textLanguages = []
    for k, v in data['text'].items():
        textLanguage = LanguageViewItem()
        textLanguage.DisplayName = v['name']
        textLanguage.Code = k
        setattr(textLanguage, 'Voices', voicesByPrimaryLanguageCode.get(k, []))
        textLanguages.append(textLanguage)

    # Sort languages alphabetically by DisplayName before printing the list
    textLanguages.sort(key=lambda x: x.DisplayName)
    for textLanguage in textLanguages:
        print(textLanguage.DisplayName)
        print('  API code: %s' % (textLanguage.Code))
        if (len(textLanguage.Voices) <= 0):
            print('  No voices available')
        else:
            print('  Available voices:')
            for voice in textLanguage.Voices:
                print('    %s (Gender: %s, Region: %s, API Code: %s)' % (voice.DisplayName, voice.Gender, voice.RegionName, voice.Code))

    print('--------------------------------------------------\n')


if __name__ == "__main__":
    list_supported_languages()



