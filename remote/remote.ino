#include <IRremote.h>

const int LED_PIN = 3;
const int IR_PIN = 8;
IRrecv ir(IR_PIN);
decode_results res;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(9600);
  ir.enableIRIn(); 
}

bool on = false;
unsigned long last = millis();

void dump(decode_results *results) {
  int count = results->rawlen;
  if (results->decode_type == UNKNOWN) {
    Serial.println("Could not decode message");
  } 
  else {
    if (results->decode_type == NEC) {
      Serial.print("Decoded NEC: ");
    } 
    else if (results->decode_type == SONY) {
      Serial.print("Decoded SONY: ");
    } 
    else if (results->decode_type == RC5) {
      Serial.print("Decoded RC5: ");
    } 
    else if (results->decode_type == RC6) {
      Serial.print("Decoded RC6: ");
    }
    Serial.print(results->value, HEX);
    Serial.print(" (");
    Serial.print(results->bits, DEC);
    Serial.println(" bits)");
  }
  Serial.print("Raw (");
  Serial.print(count, DEC);
  Serial.print("): ");

  for (int i = 0; i < count; i++) {
    if ((i % 2) == 1) {
      Serial.print(results->rawbuf[i]*USECPERTICK, DEC);
    } 
    else {
      Serial.print(-(int)results->rawbuf[i]*USECPERTICK, DEC);
    }
    Serial.print(" ");
  }
  Serial.println("");
}

void loop() {
  if (ir.decode(&res)) {
    if (millis() - last > 250) {
      digitalWrite(LED_PIN, HIGH);
      //dump(&res);
      Serial.println(res.value, HEX);
    }
    last = millis();      
    digitalWrite(LED_PIN, LOW);
    ir.resume(); 
  }
}
