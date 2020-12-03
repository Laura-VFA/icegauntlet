module IceGauntlet {

  exception Unauthorized {};
  exception RoomAlreadyExists {};
  exception RoomNotExists {};
  exception WrongRoomFormat {};

  interface Authentication {
    void changePassword(string user, string currentPassHash, string newPassHash) throws Unauthorized;
    string getNewToken(string user, string passwordHash) throws Unauthorized;
    bool isValid(string token);
  };

  interface RoomManager {
    void publish(string token, string roomData) throws Unauthorized, RoomAlreadyExists, WrongRoomFormat;
    void remove(string token, string roomName) throws Unauthorized, RoomNotExists;
  };

  interface Dungeon {
    string getRoom() throws RoomNotExists;
  };

};
