import React, { createContext, useState, useEffect } from 'react';
import axios from 'axios';

export const UserContext = createContext();

export function UserProvider({ children }) {
  const [userId, setUserId] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Ensure default user exists and get ID
  useEffect(() => {
    async function ensureUser() {
      try {
        // Try to get default user
        const { data: users } = await axios.get('/api/user/_all');

        if (users.length > 0) {
          setUserId(users[0].id || users[0]._id);
          setUser(users[0]);
        } else {
          // Create default user
          const { data: newUser } = await axios.post('/api/user/_new', {
            email: 'default@deadman.local',
            name: 'DeadMan'
          });
          setUserId(newUser.id);
          setUser(newUser);
        }
      } catch (error) {
        console.error('Failed to ensure user:', error);
        // Use fallback ID for development
        setUserId('default');
      } finally {
        setLoading(false);
      }
    }

    ensureUser();
  }, []);

  const logUserIn = (userData) => {
    setUser(userData);
    setUserId(userData.id || userData._id);
  };

  const logUserOut = () => {
    setUser(null);
    setUserId(null);
  };

  return (
    <UserContext.Provider value={{ userId, user, loading, logUserIn, logUserOut }}>
      {children}
    </UserContext.Provider>
  );
}
