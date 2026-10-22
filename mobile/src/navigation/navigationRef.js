import { createNavigationContainerRef } from '@react-navigation/native';

// Lets components rendered outside a screen (e.g. the side menu) navigate.
export const navigationRef = createNavigationContainerRef();

export const navigateTo = (name, params) => {
  if (navigationRef.isReady()) {
    navigationRef.navigate(name, params);
  }
};
