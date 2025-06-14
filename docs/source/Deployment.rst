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

3. Install FTP server

4. Configure camera

   1. Which folder to upload to

   2. 3 shots

   3. Video

5. Change deterrance sounds

.. _Microseven M7: https://www.microseven.com/product/1080P%20Open%20Source%20Remote%20Managed-M7B1080P-WPSAA.html
.. _WSL: https://learn.microsoft.com/en-us/windows/wsl/install
.. _Best practices for setting up a WSL development environment: https://learn.microsoft.com/en-us/windows/wsl/setup/environment#set-up-your-linux-username-and-password
