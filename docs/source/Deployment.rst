Deployment
==========

Deployment of the PEECYG system involves several key steps to ensure that the camera traps are set up correctly and function as intended. This includes selecting appropriate camera locations, ensuring weatherproofing, and considering power supply options.

Camera Deployment
-----------------

We have tested PumaGuard with the following camera model:

- `Microseven M7`_

The main considerations when choosing a camera for deployment are that it can upload images and videos to a remote FTP server and is WiFi capable.

Deploy PumaGuard on a Windows laptop
------------------------------------

A Windows laptop can be used to deploy PumaGuard. Since all communication is done via WiFi, the laptop can be placed anywhere within the range of the wireless network.

Install / Enable WSL
~~~~~~~~~~~~~~~~~~~~

Windows Subsystem for Linux (`WSL`_) is required to run PumaGuard on a Windows laptop. Follow these steps to install and enable WSL:

1. Open PowerShell as Administrator
    .. code-block:: powershell

        wsl --install
2. Once you have installed WSL, you will need to create a user account and password for your newly installed Linux distribution. See the `Best practices for setting up a WSL development environment`_ guide to learn more.

Automated Installation
----------------------

3. Run installer script
    .. code-block:: bash

        curl --output install-pumaguard.sh https://raw.githubusercontent.com/PEEC-Nature-Youth-Group/pumaguard/refs/heads/main/scripts/install-pumaguard.sh && bash ./install-pumaguard.sh

Manual Installation
-------------------

3. Install FTP server
    .. code-block:: bash

        sudo apt install vsftpd

4. Configure camera (The Video tab, ``http://CAMERA_IP_ADDRESS/videosetup.html``)
    1. Video tab
        - Brightness (``http://CAMERA_IP_ADDRESS/videodisplay.html``)
            - Change brightness to 25 (could vary depending on site). Default brightness at our sight results in pictures that are too bright and many false positives.
        - Motion record tab (``http://CAMERA_IP_ADDRESS/motiondetect.html``)
            - Set up motion detection zones
            - Setup motion detection zone (or zones) by drawing rectangle over area you want animals detected. You should see a red rectangle for each detection zone you set up in the field of view. This avoid the cameras from taking pictures of cars in the street, branches moving in the wind, etc.
            - Set up the parameters
                - Sensitivity level: 30 (don’t need to be very sensitive to take a photo of a puma)
                - Photo size: XL (works with small pictures too but this provides a better record of the photos)
                - Snap shot count: 3 (this takes three shots per detection)
                - Upload snapshot to FTP (you may want to check email option first to make sure camera sends pictures to your email before figuring out FTP)
                - Schedule motion detection record (we only trained neural network to night for now)
                - Set duration 1: 00:00 – 07:30
                - Set duration 2: 20:00 – 24:00
5. Change deterrence sounds

.. _Microseven M7: https://www.microseven.com/product/1080P%20Open%20Source%20Remote%20Managed-M7B1080P-WPSAA.html
.. _WSL: https://learn.microsoft.com/en-us/windows/wsl/install
.. _Best practices for setting up a WSL development environment: https://learn.microsoft.com/en-us/windows/wsl/setup/environment#set-up-your-linux-username-and-password
