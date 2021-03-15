# Installing RadBot as a Systemd Service

(These instructions were tested on Ubuntu 20.04 LTS)

1. Create a non-root user to run the RadBot process

    ```
    useradd -m -s /bin/bash radbot
    ```

2. Copy all the RadBot files into the radbot user home directory

    ```
    /home/radbot/RadBot/
    ```

3. Copy the radbot.service file into /etc/systemd/system/

    ```
    sudo cp radbot.service /etc/systemd/system/
    ```

    The service file is configured to run as the radbot user and group and use
    /home/radbot/RadBot as the working directory. You shouldn't need to change any
    configuration values if you've set up the radbot user as above.


4. Let systemd know about the new service file by running:

    ```
    sudo systemctl daemon-reload
    ```

5. Start the radbot service:

    ```
    sudo systemctl start radbot
    ```

6. Check the running status as follows:

    ```
    sudo systemctl status radbot
    ```

    You should see something similar to below:

    ```
    ● radbot.service - RadBot Service
     Loaded: loaded (/etc/systemd/system/radbot.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2021-03-15 17:16:17 UTC; 4s ago
   Main PID: 105129 (python3.9)
      Tasks: 11 (limit: 76859)
     Memory: 97.9M
     CGroup: /system.slice/radbot.service
             └─105129 /usr/bin/python /home/radbot/RadBot/RadBot.py
    ```

7. If the bot runs successfully, then enable the service as follows so that it will automatically start up on server reboot:

    ```
    sudo systemctl enable radbot
    ```
