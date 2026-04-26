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
