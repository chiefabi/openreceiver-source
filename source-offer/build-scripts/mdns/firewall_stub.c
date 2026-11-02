/* Ersatz für mDNSWindows/SystemService/Firewall.cpp (COM-Firewall-Zugriff und Dateifreigabe-Prüfung).
 * Der OpenReceiver richtet die Firewall-Regel selbst ein; Dateifreigaben (SMB) werden nicht beworben. */
#include <windows.h>
long mDNSAddToFirewall(LPWSTR executable, LPWSTR name) { (void) executable; (void) name; return 0; }
BOOL mDNSIsFileAndPrintSharingEnabled(BOOL *retry) { if (retry) *retry = FALSE; return FALSE; }
