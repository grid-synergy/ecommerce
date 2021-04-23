// ----------------------------------------------------------------------------
// written by:  Lawrence McDaniel
//              lpm0073@gmail.com
//              https://lawrencemcdaniel.com
//
// usage:       Base Jenkins pipeline script to build, test, 
//              merge to koa.master.
//
//              Jenkins host: https://jenkins.gsedxlms.com/
//
//              Jenkins variables: https://jenkins.gsedxlms.com/env-vars.html/
// ----------------------------------------------------------------------------
def gv 

pipeline {

    agent { docker { image 'python:3.5.1' } }
    //agent any 

    stages {

        stage("init") {

            steps {
                script {
                    gv = load "Jenkins.pipeline.groovy"
                    gv.initEnvironment()
                }
            }

        }

        stage('build') {

            steps {
                script {
                    if (gv.isGSBranch()) {
                        echo 'this is a gs/ branch: building'
                    } else {
                        echo 'this is not a gs/ branch but we will build it anyway'
                    }
                    gv.buildApp()
                }
            }

        }

        stage("test") {

            steps {
                script {
                    if (gv.isGSBranch()) {
                        echo 'this is a gs/ branch: testing'
                    } else {
                        echo 'this is not a gs/ branch but we will test anyway'
                    }
                    gv.testApp()
                }
            }

        }

        stage("deploy") {

            steps {

                script {
                    if (gv.isGSBranch()) {
                        gv.deployApp()
                    } else {
                        echo 'this is not a gs/ branch. not deploying'
                    }
                }

                // requires plugins: Credentials, Credentials Binding
                //withCredentials([
                //    usernamePassword(
                //        credentials: 'gs-edx-staging', 
                //        usernameVariable: USER, 
                //        passwordVariable: PWD)
                //]) {
                //        // user, pwd available here.
                //        echo "username is ${USER}."
                //}
            }

        }        

    }

    // +++++++++++++++++++++++++++++++++++++++++++++++++++++++
    // THESE ARE ACTIONS THAT WE TAKE BASED ON THE JENKINS 
    // PIPELINE RESULT.
    // +++++++++++++++++++++++++++++++++++++++++++++++++++++++
   post {

        always {

            echo 'Cleaning up Jenkins environment...'

        }

        failure {
            
            echo 'Jenkins post - Failure...'

            // post a message back to the pull requests that Jenkins job failed.

        }

        success {

            echo 'Jenkins post - Success...'
            echo "This pull request / commit merged into koa.master"

        }
    }    

}