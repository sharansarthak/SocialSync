# Test Documentation

This document outlines the user stories and corresponding tests for the SocialSync application. Each user story is accompanied by a description of the functional tests that are designed to validate the application's behavior from a user's perspective.

## User Story 1: User Sign-Up

**Story:** As a new user, I want to sign up so that I can create an account in the application.

### Tests
- **Valid Sign-Up:** Enter valid name, email, password, age, and description. Expect successful registration.
- **Invalid Email:** Enter an invalid email format. Expect an error message.
- **Weak Password:** Enter a weak password. Expect an error message about password strength.
- **Missing Information:** Omit required fields. Expect an error message about missing information.
- **Duplicate Email:** Use an already registered email. Expect an error message.

## User Story 2: User Login

**Story:** As a returning user, I want to log in so that I can access my account.

### Tests
- **Valid Login:** Enter correct email and password. Expect successful login.
- **Invalid Credentials:** Enter incorrect email or password. Expect an error message.
- **Empty Fields:** Leave email or password fields empty. Expect an error message.

## User Story 3: Profile Update

**Story:** As a registered user, I want to update my profile so that I can change my personal information.

### Tests
- **Valid Update:** Change profile details with valid data. Expect successful update.
- **Invalid Email:** Use an invalid email format. Expect an error message.
- **Age Limit:** Enter an age outside the permissible range. Expect an error message.

## User Story 4: Event Creation

**Story:** As a user, I want to create an event so that I can invite others to participate.

### Tests
- **Valid Event Creation:** Create an event with all required details. Expect successful creation.
- **Missing Details:** Omit essential details. Expect an error message.
- **Past Date:** Set the event date in the past. Expect an error message.


### User Story 5: Uploading a Profile Picture

**Story:** As a user, I want to upload my profile picture so that my profile is personalized.

#### Tests
- **Valid Upload:** Successfully upload a valid image file as a profile picture.
- **Invalid File Type:** Attempt to upload a non-image file and expect an error message.
- **Large File Size:** Try uploading an oversized image file and expect an error message.
- **No File Provided:** Send a request without a file and expect an error message about the missing file.

### User Story 6: Retrieving a User's Profile Picture

**Story:** As a user, I want to view my profile picture to ensure it's correct.

#### Tests
- **Valid Request:** Request the profile picture for an existing user and expect to receive the URL.
- **Non-existent User:** Request a picture for a user that doesn't exist and expect an error message.
- **User Without Picture:** Request a picture for a user who hasn't uploaded one and expect an appropriate message.

### User Story 7: Getting All Events

**Story:** As a user, I want to view all events to find ones I might be interested in.

#### Tests
- **Retrieve Events:** Access the endpoint to get a list of all events and expect a detailed list.
- **Empty Event List:** If there are no events, ensure the response is handled gracefully.

### User Story 8: Event Search with Filters

**Story:** As a user, I want to search for events using specific filters to find those that match my interests.

#### Tests
- **Search with Various Filters:** Use different combinations of filters and verify the results match the criteria.
- **Invalid Filters:** Provide invalid filter values and expect an error message or no results.
- **No Filters:** Send a request without any filters and expect all events or guidance on using filters.
