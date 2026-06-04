SCHEMA = {
    'magnification' : {'required' : True, 'type':'float'},
    'device' : {
        'required' : True,
        'type' : 'dict',
        'schema' : {
            'name' : {
                'required' : True,
                'type' : 'string'
            },
            'x_channel' : {
                'required' : True,
                'type' : 'number',
                'min' : 0,
                'max' : 1
            },
            'y_channel' : {
                'required' : True,
                'type' : 'number',
                'min' : 0,
                'max' : 1
            },
            'apd_channel' : {
                'required' : True,
                'type' : 'number',
                'min' : 0,
                'max' : 7
            },
        }
    }
}

EXP_SETTINGS = {
    'scan_size_um' : {'required' : True, 'type':'float'},
    'aq_time_ms' : {'required' : True, 'type':'float'},
    'averaging' : {'required' : True, 'type':'number', 'min' : 1},
    'adc_range' : {'required' : True, 'type':'string', 'allowed': ['0.2', '1', '5', '10']},
    'resolution' : {'required' : True, 'type':'string', 'allowed': ['440', '720', '1080', '2160']}
}