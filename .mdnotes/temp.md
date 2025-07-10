                    canteenMenu = app_settings.get('CanteenMenu')
                    mode = canteenMenu.get('currentMode')
                    print("MODE : ", mode)

                    if mode == "device": 
                        order = user_order
