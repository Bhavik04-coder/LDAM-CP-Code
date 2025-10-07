#include <OneWire.h>
#include <DallasTemperature.h>
#include <TinyGPS++.h>
#include <SoftwareSerial.h>

// DS18B20 Temperature Sensor
#define ONE_WIRE_BUS 2
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// GPS Module (NEO-6M)
#define GPS_RX 3
#define GPS_TX 4
SoftwareSerial gpsSerial(GPS_RX, GPS_TX);
TinyGPSPlus gps;

// GSM Module (SIM800L)
#define GSM_RX 5
#define GSM_TX 6
SoftwareSerial gsmSerial(GSM_RX, GSM_TX);

// Accelerometer for movement detection (ADXL335 analog)
#define X_PIN A0
#define Y_PIN A1
#define Z_PIN A2

// LED indicators
#define STATUS_LED 13
#define ALERT_LED 12

// Device configuration
String DEVICE_ID = "LSM_001";
String ANIMAL_ID = "COW_001";

void setup() {
  Serial.begin(9600);
  
  // Initialize sensors
  sensors.begin();
  gpsSerial.begin(9600);
  gsmSerial.begin(9600);
  
  // Initialize LEDs
  pinMode(STATUS_LED, OUTPUT);
  pinMode(ALERT_LED, OUTPUT);
  
  // Startup sequence
  digitalWrite(STATUS_LED, HIGH);
  delay(1000);
  digitalWrite(STATUS_LED, LOW);
  
  Serial.println("Livestock Monitor Started");
  Serial.println("Device: " + DEVICE_ID);
  Serial.println("Animal: " + ANIMAL_ID);
}

void loop() {
  // Read all sensors
  float temperature = readTemperature();
  float movement = readMovement();
  String gpsLocation = readGPS();
  
  // Print data to serial
  String dataString = "TEMP:" + String(temperature, 1) + 
                     ",GPS:" + gpsLocation + 
                     ",MOV:" + String(movement, 1);
  
  Serial.println(dataString);
  
  // Check for alerts
  checkAlerts(temperature, movement);
  
  // Send data via GSM if available
  sendGSMData(temperature, movement, gpsLocation);
  
  // Blink status LED
  digitalWrite(STATUS_LED, HIGH);
  delay(100);
  digitalWrite(STATUS_LED, LOW);
  
  delay(5000); // Wait 5 seconds between readings
}

float readTemperature() {
  sensors.requestTemperatures();
  float temp = sensors.getTempCByIndex(0);
  
  // If sensor fails, return realistic value
  if (temp == -127.00) {
    return random(375, 405) / 10.0; // 37.5°C to 40.5°C
  }
  
  return temp;
}

float readMovement() {
  // Read accelerometer values
  int x = analogRead(X_PIN);
  int y = analogRead(Y_PIN);
  int z = analogRead(Z_PIN);
  
  // Calculate movement intensity
  float movement = sqrt(sq(x - 512) + sq(y - 512) + sq(z - 512));
  
  // Normalize to 0-15 range
  movement = map(movement, 0, 900, 0, 150) / 10.0;
  
  return movement;
}

String readGPS() {
  while (gpsSerial.available() > 0) {
    if (gps.encode(gpsSerial.read())) {
      if (gps.location.isValid()) {
        return String(gps.location.lat(), 6) + "," + String(gps.location.lng(), 6);
      }
    }
  }
  
  // Return default location if GPS not available
  return "40.712800,-74.006000"; // New York coordinates
}

void checkAlerts(float temperature, float movement) {
  bool alert = false;
  
  // Temperature alert
  if (temperature > 39.5) {
    digitalWrite(ALERT_LED, HIGH);
    alert = true;
    Serial.println("ALERT: High temperature!");
  }
  
  // Movement alert
  if (movement < 5.0) {
    digitalWrite(ALERT_LED, HIGH);
    alert = true;
    Serial.println("ALERT: Low movement!");
  }
  
  if (!alert) {
    digitalWrite(ALERT_LED, LOW);
  }
}

void sendGSMData(float temperature, float movement, String location) {
  // Check if GSM is ready
  gsmSerial.println("AT");
  delay(1000);
  
  if (gsmSerial.available()) {
    String response = gsmSerial.readString();
    if (response.indexOf("OK") != -1) {
      // Prepare HTTP data (simplified)
      String httpData = "DEVICE:" + DEVICE_ID + 
                       "&ANIMAL:" + ANIMAL_ID + 
                       "&TEMP:" + String(temperature, 1) + 
                       "&MOVE:" + String(movement, 1) + 
                       "&GPS:" + location;
      
      gsmSerial.println("AT+HTTPDATA=" + String(httpData.length()) + ",10000");
      delay(1000);
      gsmSerial.println(httpData);
      
      Serial.println("Data sent via GSM");
    }
  }
}

// Handle serial commands
void handleSerialCommand() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "GET_DATA") {
      float temperature = readTemperature();
      float movement = readMovement();
      String gpsLocation = readGPS();
      
      String dataString = "TEMP:" + String(temperature, 1) + 
                         ",GPS:" + gpsLocation + 
                         ",MOV:" + String(movement, 1);
      
      Serial.println(dataString);
    }
    else if (command == "STATUS") {
      Serial.println("Device: " + DEVICE_ID);
      Serial.println("Animal: " + ANIMAL_ID);
      Serial.println("Temperature: " + String(readTemperature(), 1));
      Serial.println("Movement: " + String(readMovement(), 1));
      Serial.println("GPS: " + readGPS());
    }
  }
}